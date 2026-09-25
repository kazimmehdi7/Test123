"""AliExpress: supplier price, shipping, orders sold."""
from __future__ import annotations

import re
from typing import List, Optional

from ..fetch import BlockedError, browser_get, dump_page, looks_blocked, page_html
from ..listing import SUPPLY, Listing

ITEM_SELECTORS = ["[class*='search-item-card-wrapper']", "[class*='list--gallery--']",
                  "[class*='multi--container']", "[class*='product-snippet']", "a[href*='/item/']"]


GENERIC_FIRST_WORDS = {
    "silicone", "stainless", "steel", "wooden", "wood", "bamboo", "plastic", "glass", "metal", "cotton", "leather",
    "reusable", "non", "nonstick", "large", "small", "mini", "extra", "heavy", "portable", "electric", "wireless",
    "magnetic", "adjustable", "waterproof", "collapsible", "rechargeable", "baby", "dog", "cat", "pet", "kids",
    "kitchen", "baking", "yoga", "resistance", "car", "camping", "desk", "office", "travel", "under", "over",
    "white", "black", "clear", "natural", "organic", "premium", "professional", "universal", "upgraded", "new",
}
HOUSE_BRANDS = {"amazon basics", "amazonbasics", "amazon essentials", "basics"}
QTY_RES = [re.compile(p, re.I) for p in (
    r"\b(\d{1,3})\s*/\s*\d{1,3}\s*pcs\b",          # "1/2PCS" = choose 1 or 2 -> 1 (price shown is the smallest)
    r"\b(?:set|pack|box|lot)\s+of\s+(\d{1,3})\b",
    r"\b(\d{1,3})\s*[-\s]?\s*(?:pack|pk|pcs|pc|pieces|piece|count|ct|packs|sheets|mats)\b",
)]


def pack_qty(title: str) -> int:
    """How many units a listing sells: '4-Pack' -> 4, 'Set of 3' -> 3, '1PCS' -> 1. Default 1."""
    t = (title or "").lower()
    for rx in QTY_RES:
        m = rx.search(t)
        if m:
            n = int(m.group(1))
            if 1 <= n <= 200:
                return n
    return 1


def cost_query(title: str) -> str:
    """Amazon title -> generic supplier search. Brands and sizes don't exist on supplier listings."""
    from .risk import MAJOR_BRANDS
    t = title.lower()
    if len(t) > 60:
        t = re.split(r"[,|(\[]| - | – ", t)[0]
    for b in sorted(MAJOR_BRANDS | HOUSE_BRANDS, key=len, reverse=True):
        t = re.sub(rf"\b{re.escape(b)}\b", " ", t)
    t = re.sub(r"\b\d+(\.\d+)?\s*(oz|ml|l|inch|in|cm|mm|pcs|pack|count|ft|qt)\b", " ", t)
    t = re.sub(r"\b(set of|pack of)\s*\d+\b|\b\d+\s*-?\s*pack\b", " ", t)
    words = [w for w in re.sub(r"[^a-z\s]", " ", t).split() if len(w) > 2 and w not in {"the", "and", "for", "with", "set", "pack"}]
    # The first word of an Amazon title is usually the brand (Koolstuffs, HOTEC, NiHome...). Drop it unless
    # it's an ordinary product word, as long as at least two words remain.
    if len(words) >= 3 and words[0] not in GENERIC_FIRST_WORDS:
        words = words[1:]
    q = " ".join(words[:6])
    qty = pack_qty(title)
    return f"{q} {qty}pcs" if qty > 1 else q  # look for multi-packs first, so we compare like with like


# ------------------------------------------------------------------ search page
_NUM_GAPS = re.compile(r"(\d)\s*([.,])\s*(?=\d)")
_RS = re.compile(r"(Rs\.?|PKR|US\s?\$|\$|€|£)\s?(\d[\d,]*(?:\.\d{1,2})?)", re.I)
_FX = {"rs": 0.0036, "rs.": 0.0036, "pkr": 0.0036, "$": 1.0, "us$": 1.0, "us $": 1.0, "€": 1.09, "£": 1.27}
_ID_RES = [re.compile(r"/item/(\d{8,20})"), re.compile(r"productIds=(\d{8,20})"), re.compile(r"x_object_id%3A(\d{8,20})")]
_NPI = re.compile(r"pdp_npi=[^&]*?%21([A-Z]{3})%21([\d.]+)%21([\d.]+)%21")


def _sold(t: str) -> Optional[int]:
    m = re.search(r"(\d+(?:\.\d+)?)\s*(k|m)?\+?\s*sold", (t or "").lower().replace(",", ""))
    if not m:
        return None
    return int(float(m.group(1)) * {"k": 1000, "m": 1_000_000}.get(m.group(2) or "", 1))


def _usd(sym: str, num: str):
    rate = _FX.get(sym.lower().replace(" ", "") if sym.lower().startswith("us") else sym.lower())
    try:
        v = round(float(num.replace(",", "")) * (rate or 0), 2)
    except ValueError:
        return None
    return v if rate and 0.10 <= v <= 999 else None


def _card_text(card) -> str:
    text = re.sub(r"\s+", " ", " ".join(card.css("*::text").getall()))
    return _NUM_GAPS.sub(r"\1\2", text)          # "Rs. 1 , 572 . 07" -> "Rs. 1,572.07"


def parse_card(card) -> Optional[Listing]:
    """One search-result card -> SUPPLY Listing. Conditional prices are never used as the cost."""
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

    title = (card.css("h3::text").get() or card.css("[class*='title']::text").get()
             or card.css("img::attr(alt)").get() or "").strip()
    if len(title) < 5:
        return None

    text = _card_text(card)
    low = text.lower()
    prices = []
    for m in _RS.finditer(text):
        before = text[max(0, m.start() - 25): m.start()].lower()
        if re.search(r"(save|saves|over|shipping|off|coupon|extra)\s*$", before):
            continue  # "New shoppers save Rs.1,578", "Free shipping over Rs.3,154" are not prices
        v = _usd(m.group(1), m.group(2))
        if v:
            prices.append(v)
    # displayed order on the card: sale price first, then the struck-out original (if any)
    shown = prices[0] if prices else None
    original = prices[1] if len(prices) > 1 and prices[1] > prices[0] else None

    # cross-check with the price data AliExpress embeds in the link: CUR!original!sale!
    npi = _NPI.search(href)
    npi_ok = None
    if npi and shown:
        cur, orig_v, sale_v = npi.group(1), float(npi.group(2)), float(npi.group(3))
        sale_usd = _usd(cur, str(sale_v)) if cur != "USD" else sale_v
        npi_ok = bool(sale_usd and abs(sale_usd - shown) <= max(0.02, shown * 0.01))

    # (the m03_new_user tag in links is on every card, so only the visible text counts)
    new_shopper = "new shoppers save" in low or "new shopper price" in low
    bundle = "bundle deals" in low or "bundledeals" in href.lower()
    conditional = new_shopper or bundle
    # Conservative cost: if the shown price needs a condition, a repeat buyer pays the original price.
    cost = original if (conditional and original) else shown
    if cost is None:
        return None

    ship_cost, free_over = None, None
    fm = re.search(r"free shipping over\s*(Rs\.?|PKR|US\s?\$|\$)\s?([\d,]+(?:\.\d+)?)", text, re.I)
    if fm:
        free_over = _usd(fm.group(1), fm.group(2))
    elif re.search(r"\bfree shipping\b", low):
        ship_cost = 0.0
    sm = re.search(r"\+\s*(Rs\.?|US\s?\$|\$)\s?([\d,]+(?:\.\d+)?)\s*shipping", text, re.I)
    if sm:
        ship_cost = _usd(sm.group(1), sm.group(2))

    rating = None
    r = card.css("[class*='starRating']::text").get() or card.css("[class*='evaluation']::text").get()
    if r:
        try:
            v = float(r.strip())
            rating = v if 0 < v <= 5 else None
        except ValueError:
            pass
    sold = next((s for s in (_sold(t) for t in card.css("[class*='trade']::text").getall()) if s), None) or _sold(text)

    img = card.css("img::attr(src)").get()
    confidence = 0.55 + (0.15 if npi_ok else 0) + (0.1 if rating else 0) + (0.1 if sold else 0) - (0.1 if conditional and not original else 0)
    return Listing(source="aliexpress", side=SUPPLY, source_id=item_id, title=title,
                   url=f"https://www.aliexpress.com/item/{item_id}.html", price=cost,
                   rating=rating, sold_count=sold, shipping_cost=ship_cost,
                   image_url=("https:" + img) if img and img.startswith("//") else img,
                   confidence=round(min(confidence, 0.95), 2),
                   raw={"shown_price": shown, "original_price": original, "new_shopper_price": new_shopper,
                        "bundle_deal": bundle, "cost_basis": "original (shown price is conditional)" if cost != shown else "shown",
                        "free_shipping_over": free_over, "price_crosscheck": npi_ok, "pack_qty": pack_qty(title),
                        "ad": text.rstrip().endswith(" Ad")})


def parse_search_page(page, limit: int = 20) -> List[Listing]:
    items = []
    for sel in ITEM_SELECTORS:
        items = page.css(sel)
        if items:
            break
    out: List[Listing] = []
    for it in items:
        try:
            l = parse_card(it)
        except Exception as e:
            print(f"[aliexpress] card skipped: {e.__class__.__name__}")
            continue
        if l and all(l.source_id != x.source_id for x in out):
            out.append(l)
        if len(out) >= limit:
            break
    return out


async def search(query: str, limit: int = 6) -> List[Listing]:
    slug = re.sub(r"-+", "-", re.sub(r"[^a-z0-9-]", "", query.lower().replace(" ", "-"))).strip("-")
    page = await browser_get(f"https://www.aliexpress.com/w/wholesale-{slug}.html?g=y&SearchText={slug.replace('-', '+')}", "dynamic")
    if looks_blocked(page, ("punish", "slide to verify", "x5sec")):
        dump_page("aliexpress", page, "(blocked)")
        raise BlockedError("AliExpress served a slider CAPTCHA")
    out = parse_search_page(page, limit)
    if not out:
        dump_page("aliexpress", page, "(0 parsed)")
    return out


async def item_price(url: str) -> Optional[float]:
    page = await browser_get(url, "dynamic")
    if looks_blocked(page, ("punish", "slide to verify")):
        raise BlockedError("AliExpress served a slider CAPTCHA")
    for sel in ("[class*='price--current']", "[class*='product-price-current']", "[class*='price']"):
        texts = page.css(f"{sel} *::text").getall() or page.css(f"{sel}::text").getall()
        nums = re.findall(r"\d+\.\d{2}", "".join(texts))
        if nums:
            return float(nums[0])
    m = re.search(r'"formatedActivityPrice"\s*:\s*"[^\d]*([\d.]+)', page_html(page))
    return float(m.group(1)) if m else None
