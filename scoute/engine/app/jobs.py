"""
Two background workers, each with its own asyncio loop:
  - "interactive": user searches. Never waits behind the daily feed.
  - "batch":       feed builds and watchlist recalculation (slow, minutes to hours).
Both share the browser threads in fetch.py, so a search waits at most for one page
load of the batch worker, not for the whole feed.
Every minute the batch worker checks the clock: at FEED_HOUR_UTC it builds all feeds,
then recalculates the watchlist.
"""
from __future__ import annotations

import asyncio
import queue
import threading
from datetime import datetime

from .config import settings

_queues = {"interactive": queue.Queue(), "batch": queue.Queue()}
_state = {"last_daily": None, "running": {"interactive": False, "batch": False}}


def submit(kind: str, arg=None):
    _queues["interactive" if kind == "search" else "batch"].put((kind, arg))


async def _handle(kind: str, arg):
    from . import services
    if kind == "search":
        await services.run_search(arg)
    elif kind == "feed":
        await (services.build_feed(arg) if arg else services.build_all_feeds())
    elif kind == "watch":
        await services.recalc_watch()
    elif kind == "daily":
        await services.build_all_feeds()
        await services.recalc_watch()


def _loop(name: str):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    q = _queues[name]
    while True:
        try:
            kind, arg = q.get(timeout=60)
            _state["running"][name] = True
            loop.run_until_complete(_handle(kind, arg))
        except queue.Empty:
            pass
        except Exception as e:
            print(f"[jobs:{name}] {e.__class__.__name__}: {e}")
        finally:
            _state["running"][name] = False
        if name == "batch":
            now = datetime.utcnow()
            if now.hour == settings.feed_hour_utc and _state["last_daily"] != now.date():
                _state["last_daily"] = now.date()
                submit("daily")


def start():
    for name in _queues:
        threading.Thread(target=_loop, args=(name,), name=f"scoute-{name}", daemon=True).start()


def status() -> dict:
    return {"queued": {n: q.qsize() for n, q in _queues.items()}, "running": dict(_state["running"]),
            "last_daily": str(_state["last_daily"])}