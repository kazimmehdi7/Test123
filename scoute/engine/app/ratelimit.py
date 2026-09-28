"""
In-memory sliding-window rate limiter for auth endpoints (login/register/password-reset
requests) — the endpoints most worth protecting from a scripted brute-force or free-tier
signup-farming attack (nothing else stopped someone from registering unlimited free accounts
to bypass the 5-searches/day cap).

Per-process only: with several app instances behind a load balancer, each instance tracks its
own counts, so the effective limit is roughly (limit x instance count) rather than a hard
global cap. That's a real limitation, not a bug — closing it needs a shared store (Redis,
already an optional dependency, or a DB-backed counter). Good enough as a first line of
defense against a single-source script; pair with a WAF/proxy-level limiter for a hard
guarantee at real traffic.
"""
from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock
from typing import Dict, List

from fastapi import HTTPException, Request

_buckets: Dict[str, List[float]] = defaultdict(list)
_lock = Lock()


def rate_limit(key_prefix: str, limit: int, window_seconds: int):
    """FastAPI dependency: raises 429 once `limit` calls have landed from the same client IP
    within `window_seconds`, for this specific key_prefix (endpoints don't share buckets)."""
    def dep(request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        key = f"{key_prefix}:{ip}"
        now = time.time()
        cutoff = now - window_seconds
        with _lock:
            bucket = _buckets[key]
            while bucket and bucket[0] < cutoff:
                bucket.pop(0)
            if len(bucket) >= limit:
                raise HTTPException(429, "Too many attempts. Wait a few minutes and try again.")
            bucket.append(now)
            # Opportunistic cleanup so long-idle IPs don't accumulate forever in memory.
            if len(_buckets) > 20_000:
                for k in [k for k, v in _buckets.items() if not v or v[-1] < cutoff]:
                    del _buckets[k]
    return dep
