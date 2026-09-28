"""
Cross-instance coordination for jobs that must run at most once even when several app
instances share one database (e.g. behind a load balancer at real user counts).

Without this, two instances each running their own background worker (see jobs.py) both
decide "it's FEED_HOUR_UTC, build today's feed" at the same moment and race to delete/insert
the same day's Opportunity rows — or both recalculate the watchlist/Sentinel and each send
their own alert email for the same threshold crossing.

Only meaningful on Postgres, which has session-scoped advisory locks. SQLite has no such
primitive and is documented (README) as single-instance/local-only anyway, so there is only
ever one worker to coordinate — the lock is a no-op there.
"""
from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import text

from .config import settings
from .db import engine


@contextmanager
def advisory_lock(key: int):
    """Try to take a Postgres session advisory lock. Yields True if acquired (caller should
    proceed) or False if another instance already holds it (caller should skip this run —
    it means a sibling instance is doing this exact job right now)."""
    if not settings.database_url.startswith("postgres"):
        yield True
        return
    conn = engine.connect()
    got = False
    try:
        got = bool(conn.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": key}).scalar())
        yield got
    finally:
        if got:
            try:
                conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": key})
            except Exception:
                pass
        conn.close()


# Fixed, distinct keys per coordinated job kind — must stay stable across deploys (an
# instance on an old key and one on a new key would no longer see each other's lock).
LOCK_KEYS = {"feed": 911_004, "watch": 911_002, "sentinel": 911_003, "daily": 911_001}
