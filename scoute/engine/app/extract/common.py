"""
Shared pieces for price extraction: the Candidate type, money parsing and
safe helpers around Scrapling pages. No network, no side effects.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, List, Optional

from ..fetch import FX

MIN_PRICE, MAX_PRICE = 0.50, 10_000.0
MAX_TEXT = 200_000          # never scan more than this many characters of a page

# Currency must be present — a bare number is never treated as a price.
MONEY_RE = re.compile(
    r"(US\s?\$|\$|£|€|₹|₨|PKR|Rs\.?|INR|USD|EUR|GBP)\s?"
    r"(\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)",
)
CURRENCY = {"US$": "USD", "US $": "USD", "$": "USD", "USD": "USD", "£": "GBP", "GBP": "GBP", "€": "EUR", "EUR": "EUR",
            "₹": "INR", "INR": "INR", "₨": "PKR", "PKR": "PKR", "Rs": "PKR", "Rs.": "PKR"}

# Text right before a price that means "this is not the price you pay for one unit"
NOT_THE_PRICE = re.compile(
    r"(list price|typical price|was:?|save|savings|you save|coupon|off\b|per count|/\s*count|/\s*ounce|/\s*oz|"
    r"/\s*fl oz|/\s*lb|/\s*item|/\s*unit|shipping|delivery|import fees|deposit|used from|new from|"
    r"trade-in|monthly|/mo\b|installment)[\s:.\-]*$", re.I)
SPLIT_RE = re.compile(r"(\d)[.,]\s+(\d{2})(?!\d)")
NOT_AFTER = re.compile(r"^\s*(/\s*(count|ounce|oz|fl oz|lb|item|unit|mo)|shipping|delivery|off\b)", re.I)


@dataclass
class Candidate:
    value: float            # USD
    raw: str                # the text it came from (for debugging and the AI check)
    currency: str = "USD"
    context: str = ""       # ~120 chars around it


@dataclass
class MethodResult:
    method: str
    candidates: List[Candidate] = field(default_factory=list)   # first = this method's choice
    error: Optional[str] = None

    @property
    def primary(self) -> Optional[Candidate]:
        return self.candidates[0] if self.candidates else None


def canon_currency(sym: str) -> str:
    s = sym.replace(" ", "")
    return CURRENCY.get(sym.strip(), CURRENCY.get(s, "USD"))


def to_usd(amount: float, currency: str) -> Optional[float]:
    rate = FX.get(currency)
    if rate is None:
        return None
    v = round(amount * rate, 2)
    return v if MIN_PRICE <= v <= MAX_PRICE else None


def parse_money(text: str, context: str = "", default_currency: Optional[str] = None) -> Optional[Candidate]:
    """'$1,299.99' -> Candidate(1299.99). Bare numbers only allowed when default_currency is given."""
    if not text:
        return None
    t = text.strip().replace("\u00a0", " ")
    m = MONEY_RE.search(t)
    if m:
        cur, num = canon_currency(m.group(1)), m.group(2)
    elif default_currency:
        n = re.search(r"\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?", t)
        if not n:
            return None
        cur, num = default_currency, n.group(0)
    else:
        return None
    try:
        amount = float(num.replace(",", ""))
    except ValueError:
        return None
    usd = to_usd(amount, cur)
    if usd is None:
        return None
    return Candidate(value=usd, raw=t[:60], currency=cur, context=(context or t)[:160])


def money_in_text(text: str) -> List[Candidate]:
    """Every currency amount in a block of text, skipping list prices, unit prices, shipping, coupons."""
    out: List[Candidate] = []
    text = (text or "")[:MAX_TEXT]
    # Amazon renders "$", "14.", "99" as separate spans; joined text reads "$ 14. 99" -> "$14.99"
    text = SPLIT_RE.sub(r"\1.\2", text)
    for m in MONEY_RE.finditer(text):
        before = text[max(0, m.start() - 40): m.start()]
        after = text[m.end(): m.end() + 20]
        if NOT_THE_PRICE.search(before) or NOT_AFTER.search(after):
            continue
        c = parse_money(m.group(0), context=text[max(0, m.start() - 60): m.end() + 60])
        if c:
            out.append(c)
    return out


def page_currency(node: Any, zones: List[str]) -> str:
    """The currency the page shows prices in (Amazon shows PKR/INR/... based on the visitor's IP).
    Used for numbers that carry no symbol, like hidden inputs and embedded JSON."""
    counts: dict = {}
    texts = [all_text(z, 3000) for sel in zones for z in css(node, sel)[:1]]
    if not any(texts):
        texts = [all_text(node, 20000)]
    for t in texts:
        for m in MONEY_RE.finditer(t):
            cur = canon_currency(m.group(1))
            counts[cur] = counts.get(cur, 0) + 1
    return max(counts, key=counts.get) if counts else "USD"


def same(a: float, b: float) -> bool:
    return abs(a - b) <= max(0.02, 0.01 * max(a, b))


# ---------------------------------------------------------------- page helpers
def css(node: Any, selector: str) -> list:
    """Scrapling .css() that never raises on a bad selector from selectors.json."""
    try:
        return list(node.css(selector))
    except Exception:
        return []


def css_first_text(node: Any, selector: str) -> Optional[str]:
    try:
        v = node.css(selector).get()
        return str(v).strip() if v else None
    except Exception:
        return None


def all_text(node: Any, limit: int = 4000) -> str:
    try:
        parts = node.css("*::text").getall()
    except Exception:
        return ""
    return re.sub(r"\s+", " ", " ".join(str(p) for p in parts))[:limit]


def page_source(page: Any) -> str:
    for attr in ("html_content", "body", "content"):
        v = getattr(page, attr, None)
        if v is None or callable(v):
            continue
        if isinstance(v, (bytes, bytearray)):
            v = v.decode("utf-8", "ignore")
        if str(v).strip():
            return str(v)[:MAX_TEXT * 5]
    return ""


@lru_cache(maxsize=None)
def rules(site: str) -> dict:
    path = os.path.join(os.path.dirname(__file__), "..", "data", "selectors.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if site not in data:
        raise KeyError(f"No selectors for site '{site}' in data/selectors.json")
    return data[site]


def reload_rules():
    rules.cache_clear()


def parse_json_safely(text: str) -> Any:
    try:
        return json.loads(text)
    except (ValueError, TypeError, RecursionError):
        return None