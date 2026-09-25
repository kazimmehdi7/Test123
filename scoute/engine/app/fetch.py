"""
The one place that talks to the network.

browser_get(): real browser via Scrapling. Each profile owns one long-lived thread
with one browser session, because Playwright's sync API can't run inside an
asyncio loop and the async version breaks under uvicorn on Windows.
"""
from __future__ import annotations

import asyncio
import atexit
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

import httpx

from .config import settings


class BlockedError(Exception):
    """Site served a CAPTCHA / block page."""


PROFILES: Dict[str, Dict[str, Any]] = {
    "stealthy": {"session": "StealthySession", "fetcher": "StealthyFetcher",
                 "options": {"headless": True, "network_idle": True, "disable_resources": False}},
    "light":    {"session": "StealthySession", "fetcher": "StealthyFetcher",
                 "options": {"headless": True, "network_idle": False, "disable_resources": True}},
    "dynamic":  {"session": "DynamicSession", "fetcher": "DynamicFetcher",
                 "options": {"headless": True, "network_idle": True}, "fetch_options": {"wait": 4000}},
}
HEADERS = {"Accept-Language": "en-US,en;q=0.9"}


class _Worker:
    def __init__(self, profile: str):
        self.spec = PROFILES[profile]
        self.profile = profile
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"browser-{profile}")
        self.session = None
        self.no_session = False

    def _opts(self) -> Dict[str, Any]:
        o = dict(self.spec["options"])
        if settings.proxy_url:
            o["proxy"] = settings.proxy_url
        return o

    def _open(self):
        try:
            import scrapling.fetchers as sf
            cls = getattr(sf, self.spec["session"])
            try:
                s = cls(**self._opts(), extra_headers=HEADERS)
            except TypeError:
                s = cls(**self._opts())
            s.__enter__()
            self.session = s
            print(f"[fetch] browser session opened ({self.profile})")
        except Exception as e:
            print(f"[fetch] no session for {self.profile} ({e.__class__.__name__}); one-shot mode")
            self.no_session = True

    def _close(self):
        if self.session is not None:
            try:
                self.session.__exit__(None, None, None)
            except Exception:
                pass
            self.session = None

    def fetch_sync(self, url: str):
        fo = dict(self.spec.get("fetch_options", {}))
        if self.session is None and not self.no_session:
            self._open()
        if self.session is not None:
            try:
                try:
                    return self.session.fetch(url, **fo)
                except TypeError:
                    return self.session.fetch(url)
            except Exception as e:
                print(f"[fetch] session failed ({e.__class__.__name__}); one-shot fetch")
                self._close()
        import scrapling.fetchers as sf
        fetcher = getattr(sf, self.spec["fetcher"])
        try:
            return fetcher.fetch(url, extra_headers=HEADERS, **self._opts(), **fo)
        except TypeError:
            return fetcher.fetch(url, headless=True)


_workers: Dict[str, _Worker] = {}


@atexit.register
def _shutdown():
    for w in _workers.values():
        try:
            w.pool.submit(w._close).result(timeout=10)
        except Exception:
            pass
async def close_all():
    """Close every browser session cleanly, before the program exits.
    Without this the browser driver can still be mid-request when Python quits (EPIPE on exit)."""
    loop = asyncio.get_running_loop()
    for name, w in list(_workers.items()):
        try:
            await asyncio.wait_for(loop.run_in_executor(w.pool, w._close), timeout=15)
        except Exception as e:
            print(f"[fetch] closing {name}: {e.__class__.__name__}")
        w.pool.shutdown(wait=False)
    _workers.clear()
    

async def browser_get(url: str, profile: str = "stealthy", retries: int = 2):
    if profile not in _workers:
        _workers[profile] = _Worker(profile)
    last: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            t = time.time()
            page = await asyncio.get_running_loop().run_in_executor(_workers[profile].pool, _workers[profile].fetch_sync, url)
            print(f"[fetch] {profile} {getattr(page, 'status', '?')} {time.time() - t:.1f}s {url[:90]}")
            return page
        except Exception as e:
            last = e
            print(f"[fetch] attempt {attempt} failed: {e.__class__.__name__}: {str(e)[:120]}")
            await asyncio.sleep(2 * attempt)
    raise last or RuntimeError("browser_get failed")


async def http(method: str, url: str, **kw) -> httpx.Response:
    opts: Dict[str, Any] = {"timeout": kw.pop("timeout", 20.0), "follow_redirects": True}
    if settings.proxy_url:
        opts["proxy"] = settings.proxy_url
    async with httpx.AsyncClient(**opts) as c:
        return await c.request(method, url, **kw)


def page_html(page: Any) -> str:
    for attr in ("html_content", "body", "content"):
        v = getattr(page, attr, None)
        if v is None or callable(v):
            continue
        if isinstance(v, (bytes, bytearray)):
            v = v.decode("utf-8", "ignore")
        if str(v).strip():
            return str(v)
    return ""


def dump_page(name: str, page: Any, note: str = ""):
    """Save a page that parsed to nothing, so selectors can be fixed from real HTML."""
    try:
        os.makedirs("debug", exist_ok=True)
        path = os.path.join("debug", f"{name}_last.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(page_html(page))
        print(f"[fetch] saved {path} {note}")
    except OSError:
        pass


def looks_blocked(page: Any, extra: tuple = ()) -> bool:
    try:
        title = (page.css("title::text").get() or "").lower()
    except Exception:
        title = ""
    html = page_html(page)[:20000].lower()
    marks = ("robot check", "captcha", "sorry, we just need", "enter the characters", "unusual traffic") + tuple(extra)
    return getattr(page, "status", 200) in (403, 429, 503) or any(m in title or m in html for m in marks)


FX = {"USD": 1.0, "PKR": 0.0036, "INR": 0.012, "GBP": 1.27, "EUR": 1.09}
SYMBOLS = [("PKR", "PKR"), ("Rs", "PKR"), ("₨", "PKR"), ("INR", "INR"), ("₹", "INR"), ("£", "GBP"), ("€", "EUR"), ("$", "USD")]


def to_usd(text: str):
    """'PKR 3,872' -> (13.94, 'PKR'); '$14.99' -> (14.99, 'USD')."""
    if not text:
        return None, "USD"
    text = text.strip()
    cur = next((c for s, c in SYMBOLS if s in text), "USD")
    nums = re.findall(r"\d[\d,]*(?:\.\d+)?", text)
    if not nums:
        return None, cur
    try:
        v = float(nums[0].replace(",", ""))
    except ValueError:
        return None, cur
    return (round(v * FX.get(cur, 1.0), 2) if v > 0 else None), cur
