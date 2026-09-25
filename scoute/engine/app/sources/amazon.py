"""Amazon: search results, Movers & Shakers, and a single product's current price."""
from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import quote_plus

from ..config import settings
from ..extract import PriceResult, extract_card_price, extract_price
from ..fetch import BlockedError, browser_get, dump_page, looks_blocked
from ..listing import SELL, Listing

NOISE = {"best", "good", "cheap", "top", "great", "find", "buy", "under", "the", "a", "an", "for", "me",
         "my", "i", "want", "need", "recommend", "please", "with", "which", "what"}


def _count(t: str) -> Optional[int]:
    t = t.strip().replace("(", "").replace(")", "").replace(",", "").upper()
    try:
        if t.endswith("K"):
            return int(float(t[:-1]) * 1000)
        if t.endswith("M"):
            return int(float(t[:-1]) * 1_000_000)
        return int(float(t))
    except ValueError:
        return None


def _listing(asin: str, title: str, pr: PriceResult, **kw) -> Listing:
    """Only a VERIFIED or LIKELY price becomes Listing.price; anything else stays None."""
    url = f"https://www.amazon.com/dp/{asin}"
    raw = {**kw.pop("raw", {}), "price_status": pr.status, "price_check": pr.summary()}
    return Listing(source="amazon", side=SELL, source_id=asin, title=title, url=url,
                   price=pr.price if pr.usable else None, confidence=pr.confidence,
                   affiliate_url=f"{url}?tag={settings.amazon_tag}", raw=raw, **kw)


def clean_query(q: str) -> str:
    q2 = re.sub(r"(under|below|above|over)?\s*[\$₹£€₨]?\s*\d[\d,]*(\.\d+)?\s*(dollars?|usd|pkr|rs\.?)?", " ", q.lower())
    words = [w for w in q2.split() if w not in NOISE and len(w) > 1]
    return " ".join(words) or q.strip()


async def search(query: str, limit: int = 10) -> List[Listing]:
    url = f"https://www.amazon.com/s?k={quote_plus(clean_query(query))}&language=en_US&currency=USD&gl=US"
    page = await browser_get(url, "light")
    if not looks_blocked(page) and not page.css('[data-component-type="s-search-result"]'):
        page = await browser_get(url, "stealthy")      # full render only when the light page was empty
    if looks_blocked(page):
        dump_page("amazon_search", page, "(blocked)")
        raise BlockedError("Amazon served a robot check")
    sponsored = len(page.css('[data-component-type="sp-sponsored-result"]'))
    out: List[Listing] = []
    for card in page.css('[data-component-type="s-search-result"]'):
        asin = (card.attrib.get("data-asin") or "").strip()
        title = (card.css("h2 span::text").get() or "").strip()
        if not asin or len(title) < 5 or any(l.source_id == asin for l in out):
            continue
        pr = extract_card_price(card, "amazon", "card")
        rating = None
        m = re.search(r"(\d+\.?\d*)\s+out of", card.css(".a-icon-alt::text").get() or "")
        if m:
            rating = float(m.group(1))
        reviews = next((c for c in (_count(t) for t in card.css(".s-underline-text::text").getall()) if c), None)
        out.append(_listing(asin, title, pr, rating=rating, review_count=reviews,
                            is_sponsored=bool(card.css(".s-label-popover-default")),
                            has_prime=bool(card.css(".a-icon-prime")),
                            image_url=card.css(".s-image::attr(src)").get(),
                            raw={"sponsored_on_page": sponsored}))
        if len(out) >= limit:
            break
    if not out:
        dump_page("amazon_search", page, "(0 parsed)")
    return out


async def movers(slug: str, limit: int = 60) -> List[Listing]:
    """Amazon Movers & Shakers: biggest sales-rank gainers in the last 24h."""
    page = await browser_get(f"https://www.amazon.com/gp/movers-and-shakers/{slug}", "stealthy")
    if looks_blocked(page):
        dump_page("amazon_movers", page, "(blocked)")
        raise BlockedError("Amazon served a robot check")
    items = page.css("[id^='gridItemRoot']") or page.css(".zg-grid-general-faceout") or page.css("li.zg-item-immersion")
    out: List[Listing] = []
    for it in items:
        href = it.css("a[href*='/dp/']::attr(href)").get() or ""
        m = re.search(r"/dp/([A-Z0-9]{10})", href)
        if not m:
            continue
        text = " ".join(t.strip() for t in it.css("*::text").getall() if t.strip())
        title = (it.css("img::attr(alt)").get() or "").strip()
        if len(title) < 5:
            continue
        pr = extract_card_price(it, "amazon", "movers")
        rank = rank_before = None
        rm = re.search(r"Sales rank:\s*([\d,]+)\s*\(previously\s*([\d,]+|unranked)\)", text, re.I)
        if rm:
            rank = int(rm.group(1).replace(",", ""))
            rank_before = int(rm.group(2).replace(",", "")) if rm.group(2)[0].isdigit() else None
        rt = re.search(r"(\d\.\d) out of 5", text)
        out.append(_listing(m.group(1), title, pr, rank=rank, rank_before=rank_before,
                            rating=float(rt.group(1)) if rt else None,
                            image_url=it.css("img::attr(src)").get(), raw={"list": "movers"}))
        if len(out) >= limit:
            break
    if not out:
        dump_page("amazon_movers", page, "(0 parsed)")
    return out


async def current_price(asin: str, title: str = "") -> PriceResult:
    """Price on the product page, decided by the four-method vote. Use result.usable before trusting it."""
    url = f"https://www.amazon.com/dp/{asin}?language=en_US&currency=USD"
    page = await browser_get(url, "light")
    if looks_blocked(page):
        raise BlockedError("Amazon served a robot check")
    result = await extract_price(page, "amazon", "product", title=title)
    if result.status == "none":                        # nothing on the light page: try a full render once
        page = await browser_get(url, "stealthy")
        if looks_blocked(page):
            raise BlockedError("Amazon served a robot check")
        result = await extract_price(page, "amazon", "product", title=title)
    if result.status in ("none", "unverified"):
        dump_page("amazon_product", page, f"({result.status}: {result.reason})")
    return result