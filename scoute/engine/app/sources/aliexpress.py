"""
AliExpress supply-side scraper – final hardened version.

Features:
- Robust CAPTCHA / block detection
- Async CAPTCHA solver hook (set_captcha_solver)
- Retry with exponential backoff + jitter
- Multiple selector & price extraction fallbacks
- Conditional pricing handling (new shopper / bundle)
- Structured logging
- Same public API as original
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
from typing import Any, Callable, Dict, List, Optional, Awaitable

from ..fetch import BlockedError, browser_get, dump_page, looks_blocked, page_html
from ..listing import SUPPLY, Listing

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ITEM_SELECTORS = [
    "[class*='search-item-card-wrapper']",
    "[class*='list--gallery--']",
    "[class*='multi--container']",
    "[class*='product-snippet']",
    "a[href*='/item/']",
]

GENERIC_FIRST_WORDS = {
    "silicone", "stainless", "steel", "wooden", "wood", "bamboo", "plastic",
    "glass", "metal", "cotton", "leather", "reusable", "non", "nonstick",
    "large", "small", "mini", "extra", "heavy", "portable", "electric",
    "wireless", "magnetic", "adjustable", "waterproof", "collapsible",
    "rechargeable", "baby", "dog", "cat", "pet", "kids", "kitchen", "baking",
    "yoga", "resistance", "car", "camping", "desk", "office", "travel",
    "under", "over", "white", "black", "clear", "natural", "organic",
    "premium", "professional", "universal", "upgraded", "new",
}

HOUSE_BRANDS = {"amazon basics", "amazonbasics", "amazon essentials", "basics"}

QTY_RES = [
    re.compile(r"\b(\d{1,3})\s*/\s*\d{1,3}\s*pcs\b", re.I),
    re.compile(r"\b(?:set|pack|box|lot)\s+of\s+(\d{1,3})\b", re.I),
    re.compile(
        r"\b(\d{1,3})\s*[-\s]?\s*(?:pack|pk|pcs|pc|pieces|piece|count|ct|packs|sheets|mats)\b",
        re.I,
    ),
]

_FX: Dict[str, float] = {
    "rs": 0.0036, "rs.": 0.0036, "pkr": 0.0036,
    "$": 1.0, "us$": 1.0, "us $": 1.0, "usd": 1.0,
    "€": 1.09, "eur": 1.09,
    "£": 1.27, "gbp": 1.27,
}

_NUM_GAPS = re.compile(r"(\d)\s*([.,])\s*(?=\d)")
_RS = re.compile(r"(Rs\.?|PKR|US\s?\$|\$|€|£|USD)\s?(\d[\d,]*(?:\.\d{1,2})?)", re.I)
_ID_RES = [
    re.compile(r"/item/(\d{8,20})"),
    re.compile(r"productIds=(\d{8,20})"),
    re.compile(r"x_object_id%3A(\d{8,20})"),
]
_NPI = re.compile(r"pdp_npi=[^&]*?%21([A-Z]{3})%21([\d.]+)%21([\d.]+)%21")
_SOLD = re.compile(r"(\d+(?:\.\d+)?)\s*(k|m)?\+?\s*sold", re.I)

BLOCK_MARKERS = (
    "punish", "slide to verify", "x5sec", "captcha",
    "access denied", "unusual traffic", "verify you are human",
)

MAX_RETRIES = 3
BASE_DELAY = 1.8
MAX_DELAY = 25.0
JITTER = 0.6

# ---------------------------------------------------------------------------
# CAPTCHA solver hook
# ---------------------------------------------------------------------------
# Signature: async def solver(page) -> bool
# Return True if CAPTCHA was solved successfully, False otherwise.
CaptchaSolver = Optional[Callable[[Any], Awaitable[bool]]]
_captcha_solver: CaptchaSolver = None


def set_captcha_solver(solver: CaptchaSolver) -> None:
    """
    Register an async CAPTCHA solver.

    Example with a hypothetical CapSolver wrapper:

        async def my_solver(page):
            # extract sitekey / challenge from page, call CapSolver API,
            # inject the token back into the page, wait for success
            return True  # or False

        set_captcha_solver(my_solver)
    """
    global _captcha_solver
    _captcha_solver = solver
    logger.info("CAPTCHA solver registered: %s", "yes" if solver else "no")


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def pack_qty(title: str) -> int:
    """How many units a listing sells. Default 1."""
    t = (title or "").lower()
    for rx in QTY_RES:
        m = rx.search(t)
        if m:
            n = int(m.group(1))
            if 1 <= n <= 200:
                return n
    return 1


def cost_query(title: str) -> str:
    """Amazon title → cleaner AliExpress search query."""
    from .risk import MAJOR_BRANDS

    t = (title or "").lower()
    if len(t) > 60:
        t = re.split(r"[,|(\[]| - | – ", t)[0]

    for b in sorted(MAJOR_BRANDS | HOUSE_BRANDS, key=len, reverse=True):
        t = re.sub(rf"\b{re.escape(b)}\b", " ", t)

    t = re.sub(r"\b\d+(\.\d+)?\s*(oz|ml|l|inch|in|cm|mm|pcs|pack|count|ft|qt)\b", " ", t)
    t = re.sub(r"\b(set of|pack of)\s*\d+\b|\b\d+\s*-?\s*pack\b", " ", t)

    words = [
        w for w in re.sub(r"[^a-z\s]", " ", t).split()
        if len(w) > 2 and w not in {"the", "and", "for", "with", "set", "pack"}
    ]

    if len(words) >= 3 and words[0] not in GENERIC_FIRST_WORDS:
        words = words[1:]

    q = " ".join(words[:6])
    qty = pack_qty(title)
    return f"{q} {qty}pcs" if qty > 1 else q


def _usd(sym: str, num: str) -> Optional[float]:
    key = sym.lower().replace(" ", "")
    if key.startswith("us"):
        key = "us$"
    rate = _FX.get(key)
    if not rate:
        return None
    try:
        v = round(float(num.replace(",", "")) * rate, 2)
    except ValueError:
        return None
    return v if 0.10 <= v <= 999 else None


def _sold(text: str) -> Optional[int]:
    m = _SOLD.search((text or "").lower().replace(",", ""))
    if not m:
        return None
    mult = {"k": 1_000, "m": 1_000_000}.get((m.group(2) or "").lower(), 1)
    return int(float(m.group(1)) * mult)


def _card_text(card) -> str:
    raw = " ".join(card.css("*::text").getall())
    text = re.sub(r"\s+", " ", raw)
    return _NUM_GAPS.sub(r"\1\2", text)


def _is_blocked(page) -> bool:
    return looks_blocked(page, BLOCK_MARKERS)


async def _backoff(attempt: int) -> None:
    delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
    delay *= 1 + random.uniform(-JITTER, JITTER)
    delay = max(0.5, delay)
    logger.debug("Backoff %.1fs (attempt %d)", delay, attempt + 1)
    await asyncio.sleep(delay)


async def _fetch_with_retry(
    url: str,
    mode: str = "dynamic",
    max_retries: int = MAX_RETRIES,
) -> Any:
    """
    Fetch page with retries, block detection and optional CAPTCHA solving.
    Raises BlockedError only after all retries fail.
    """
    last_exc: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            page = await browser_get(url, mode)

            if not _is_blocked(page):
                return page

            # Blocked – try CAPTCHA solver if registered
            logger.warning("Blocked on attempt %d for %s", attempt + 1, url[:80])

            if _captcha_solver is not None:
                try:
                    solved = await _captcha_solver(page)
                    if solved:
                        logger.info("CAPTCHA solved on attempt %d", attempt + 1)
                        # Re-fetch after successful solve (solver usually injects token)
                        page = await browser_get(url, mode)
                        if not _is_blocked(page):
                            return page
                except Exception as e:
                    logger.exception("CAPTCHA solver failed: %s", e)

            # Dump for debugging
            dump_page("aliexpress", page, f"(blocked attempt {attempt + 1})")

            if attempt < max_retries:
                await _backoff(attempt)
                continue

            raise BlockedError("AliExpress served CAPTCHA / block page after retries")

        except BlockedError:
            raise
        except Exception as e:
            last_exc = e
            logger.warning("Fetch error attempt %d: %s", attempt + 1, e)
            if attempt < max_retries:
                await _backoff(attempt)
                continue
            raise

    if last_exc:
        raise last_exc
    raise BlockedError("AliExpress fetch failed after retries")


# ---------------------------------------------------------------------------
# Card parsing
# ---------------------------------------------------------------------------

def parse_card(card) -> Optional[Listing]:
    """One search-result card → SUPPLY Listing. Conditional prices are never used as cost."""
    hrefs = [a.attrib.get("href", "") for a in card.css("a")]
    item_id, href = None, ""
    for h in hrefs:
        for rx in _ID_RES:
            m = rx.search(h)
            if m:
                item_id, href = m.group(1), h
                break
        if item_id:
            break
    if not item_id:
        return None

    title = (
        card.css("h3::text").get()
        or card.css("[class*='title']::text").get()
        or card.css("img::attr(alt)").get()
        or ""
    ).strip()
    if len(title) < 5:
        return None

    text = _card_text(card)
    low = text.lower()

    prices: List[float] = []
    for m in _RS.finditer(text):
        before = text[max(0, m.start() - 25): m.start()].lower()
        if re.search(r"(save|saves|over|shipping|off|coupon|extra)\s*$", before):
            continue
        v = _usd(m.group(1), m.group(2))
        if v:
            prices.append(v)

    shown = prices[0] if prices else None
    original = prices[1] if len(prices) > 1 and prices[1] > prices[0] else None

    # Cross-check with embedded npi data
    npi_ok = None
    npi = _NPI.search(href)
    if npi and shown:
        cur, orig_v, sale_v = npi.group(1), float(npi.group(2)), float(npi.group(3))
        sale_usd = _usd(cur, str(sale_v)) if cur != "USD" else sale_v
        npi_ok = bool(sale_usd and abs(sale_usd - shown) <= max(0.02, shown * 0.01))

    new_shopper = "new shoppers save" in low or "new shopper price" in low
    bundle = "bundle deals" in low or "bundledeals" in href.lower()
    conditional = new_shopper or bundle

    # Prefer non-conditional price when available
    cost = original if (conditional and original) else shown
    if cost is None:
        return None

    ship_cost: Optional[float] = None
    free_over: Optional[float] = None

    fm = re.search(
        r"free shipping over\s*(Rs\.?|PKR|US\s?\$|\$)\s?([\d,]+(?:\.\d+)?)",
        text, re.I,
    )
    if fm:
        free_over = _usd(fm.group(1), fm.group(2))
    elif re.search(r"\bfree shipping\b", low):
        ship_cost = 0.0

    sm = re.search(
        r"\+\s*(Rs\.?|US\s?\$|\$)\s?([\d,]+(?:\.\d+)?)\s*shipping",
        text, re.I,
    )
    if sm:
        ship_cost = _usd(sm.group(1), sm.group(2))

    rating = None
    r = (
        card.css("[class*='starRating']::text").get()
        or card.css("[class*='evaluation']::text").get()
    )
    if r:
        try:
            v = float(r.strip())
            rating = v if 0 < v <= 5 else None
        except ValueError:
            pass

    sold = next(
        (s for s in (_sold(t) for t in card.css("[class*='trade']::text").getall()) if s),
        None,
    ) or _sold(text)

    img = card.css("img::attr(src)").get()
    if img and img.startswith("//"):
        img = "https:" + img

    confidence = (
        0.55
        + (0.15 if npi_ok else 0)
        + (0.10 if rating else 0)
        + (0.10 if sold else 0)
        - (0.10 if conditional and not original else 0)
    )

    return Listing(
        source="aliexpress",
        side=SUPPLY,
        source_id=item_id,
        title=title,
        url=f"https://www.aliexpress.com/item/{item_id}.html",
        price=cost,
        rating=rating,
        sold_count=sold,
        shipping_cost=ship_cost,
        image_url=img,
        confidence=round(min(confidence, 0.95), 2),
        raw={
            "shown_price": shown,
            "original_price": original,
            "new_shopper_price": new_shopper,
            "bundle_deal": bundle,
            "cost_basis": (
                "original (shown price is conditional)" if cost != shown else "shown"
            ),
            "free_shipping_over": free_over,
            "price_crosscheck": npi_ok,
            "pack_qty": pack_qty(title),
            "ad": text.rstrip().endswith(" Ad"),
        },
    )


def parse_search_page(page, limit: int = 20) -> List[Listing]:
    items = []
    for sel in ITEM_SELECTORS:
        items = page.css(sel)
        if items:
            break

    out: List[Listing] = []
    seen = set()

    for it in items:
        try:
            listing = parse_card(it)
        except Exception as e:
            logger.debug("Card skipped: %s", e.__class__.__name__)
            continue

        if listing and listing.source_id not in seen:
            seen.add(listing.source_id)
            out.append(listing)

        if len(out) >= limit:
            break

    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def search(query: str, limit: int = 6) -> List[Listing]:
    """
    Search AliExpress and return up to `limit` supply Listings.
    Handles blocking + CAPTCHA automatically when a solver is registered.
    """
    slug = re.sub(r"-+", "-", re.sub(r"[^a-z0-9-]", "", query.lower().replace(" ", "-"))).strip("-")
    url = (
        f"https://www.aliexpress.com/w/wholesale-{slug}.html"
        f"?g=y&SearchText={slug.replace('-', '+')}"
    )

    page = await _fetch_with_retry(url, "dynamic")
    out = parse_search_page(page, limit)

    if not out:
        dump_page("aliexpress", page, "(0 parsed)")
        logger.warning("No listings parsed for query: %s", query)

    return out


async def item_price(url: str) -> Optional[float]:
    """Fetch a single product page and extract the current price."""
    page = await _fetch_with_retry(url, "dynamic")

    for sel in (
        "[class*='price--current']",
        "[class*='product-price-current']",
        "[class*='price']",
    ):
        texts = page.css(f"{sel} *::text").getall() or page.css(f"{sel}::text").getall()
        nums = re.findall(r"\d+\.\d{2}", "".join(texts))
        if nums:
            try:
                return float(nums[0])
            except ValueError:
                pass

    # JSON fallback
    html = page_html(page)
    m = re.search(r'"formatedActivityPrice"\s*:\s*"[^\d]*([\d.]+)', html)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass

    return None