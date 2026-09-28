"""
Two kinds of background worker, each kind running one or more threads with its own asyncio loop:
  - "interactive": user searches. Never waits behind the daily feed.
  - "batch":       feed builds, watchlist recalculation, Sentinel recalculation (slow, minutes).
Both share the browser worker pools in fetch.py (FETCH_POOL_SIZE per profile), so a search
waits at most for a free pool slot, not for the whole feed build to finish.

INTERACTIVE_WORKERS threads all pull from the same "interactive" queue, so that many searches
can be *dispatched* concurrently instead of queuing behind one single-threaded loop — the real
concurrency ceiling is still the fetch.py browser pool size, this just stops the job dispatcher
itself from being a second, tighter bottleneck on top of that.

Every minute a batch worker checks the clock: at FEED_HOUR_UTC it builds all feeds, then
recalculates the watchlist and Sentinel. Feed builds, watch/Sentinel recalcs, and the daily
chain all take a Postgres advisory lock first (see dlock.py) — a no-op on SQLite, but on
Postgres it stops two app instances behind a load balancer from both deciding to build the
same day's feed (or both re-scanning the watchlist and each sending their own duplicate
alert email) at the same moment.
"""
from __future__ import annotations

import asyncio
import os
import queue
import threading
from datetime import datetime

from .config import settings
from .dlock import LOCK_KEYS, advisory_lock

INTERACTIVE_WORKERS = max(1, int(os.getenv("INTERACTIVE_WORKERS", "3")))
BATCH_WORKERS = max(1, int(os.getenv("BATCH_WORKERS", "1")))

_queues = {"interactive": queue.Queue(), "batch": queue.Queue()}
_worker_counts = {"interactive": INTERACTIVE_WORKERS, "batch": BATCH_WORKERS}
_active = {"interactive": 0, "batch": 0}          # number of threads of this kind currently mid-job
_active_lock = threading.Lock()
_daily_lock = threading.Lock()                    # guards the once-a-day "submit daily" check-and-set
_state = {"last_daily": None}


def submit(kind: str, arg=None):
    _queues["interactive" if kind == "search" else "batch"].put((kind, arg))


async def _handle(kind: str, arg):
    from . import services
    if kind == "search":
        # Per-search-job work — nothing to coordinate across instances, each job is independent.
        await services.run_search(arg)
        return

    key = LOCK_KEYS.get(kind)
    with advisory_lock(key) as acquired:
        if not acquired:
            print(f"[jobs] {kind}: another instance already holds this job — skipping")
            return
        if kind == "feed":
            await (services.build_feed(arg) if arg else services.build_all_feeds())
        elif kind == "watch":
            await services.recalc_watch()
        elif kind == "sentinel":
            await services.recalc_sentinel()
        elif kind == "daily":
            await services.build_all_feeds()
            await services.recalc_watch()
            await services.recalc_sentinel()


def _loop(name: str):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    q = _queues[name]
    while True:
        try:
            kind, arg = q.get(timeout=60)
            with _active_lock:
                _active[name] += 1
            try:
                loop.run_until_complete(_handle(kind, arg))
            finally:
                with _active_lock:
                    _active[name] -= 1
        except queue.Empty:
            pass
        except Exception as e:
            print(f"[jobs:{name}] {e.__class__.__name__}: {e}")
        if name == "batch":
            now = datetime.utcnow()
            with _daily_lock:
                if now.hour == settings.feed_hour_utc and _state["last_daily"] != now.date():
                    _state["last_daily"] = now.date()
                    submit("daily")


def start():
    for name, count in _worker_counts.items():
        for i in range(count):
            threading.Thread(target=_loop, args=(name,), name=f"scoute-{name}-{i}", daemon=True).start()


def status() -> dict:
    with _active_lock:
        running = {n: c > 0 for n, c in _active.items()}
    return {"queued": {n: q.qsize() for n, q in _queues.items()}, "running": running,
            "last_daily": str(_state["last_daily"])}
