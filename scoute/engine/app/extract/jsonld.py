"""
Method 1 — structured data. The most stable source because it doesn't depend on layout:
  - schema.org JSON-LD blocks (<script type="application/ld+json">)
  - microdata (itemprop="price")
  - site-specific hidden inputs / embedded JSON listed in selectors.json
"""
from __future__ import annotations

import re
from typing import Any, Iterable, List

from .common import Candidate, MethodResult, css, page_currency, page_source, parse_json_safely, parse_money, rules

SCRIPT_RE = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.S | re.I)
MAX_BLOCKS = 20


def _walk(obj: Any, depth: int = 0) -> Iterable[dict]:
    if depth > 6:
        return
    if isinstance(obj, list):
        for x in obj[:50]:
            yield from _walk(x, depth + 1)
    elif isinstance(obj, dict):
        yield obj
        for k in ("@graph", "mainEntity", "itemListElement", "item"):
            if k in obj:
                yield from _walk(obj[k], depth + 1)


def _offer_prices(product: dict, fallback_currency: str) -> List[Candidate]:
    out = []
    offers = product.get("offers")
    for off in (offers if isinstance(offers, list) else [offers]):
        if not isinstance(off, dict):
            continue
        cur = str(off.get("priceCurrency") or fallback_currency).upper()
        for key in ("price", "lowPrice"):
            v = off.get(key)
            if v is None:
                spec = off.get("priceSpecification")
                if isinstance(spec, dict):
                    v, cur = spec.get("price"), str(spec.get("priceCurrency") or cur).upper()
            if v is not None:
                c = parse_money(str(v), context=f"JSON-LD {key}", default_currency=cur)
                if c:
                    out.append(c)
                break
    return out


def extract(page: Any, site: str) -> MethodResult:
    res = MethodResult("structured")
    try:
        src = page_source(page)
        r = rules(site)
        shown = page_currency(page, r.get("price_zones", []))
        # 1) JSON-LD Product
        for block in SCRIPT_RE.findall(src)[:MAX_BLOCKS]:
            data = parse_json_safely(block.strip())
            for obj in _walk(data):
                t = obj.get("@type")
                types = t if isinstance(t, list) else [t]
                if any(str(x).lower() == "product" for x in types):
                    res.candidates += _offer_prices(obj, shown)
        # 2) microdata
        for el in css(page, "[itemprop='price']")[:5]:
            v = el.attrib.get("content") or ""
            cur_el = css(page, "[itemprop='priceCurrency']")
            cur = (cur_el[0].attrib.get("content") if cur_el else None) or shown
            c = parse_money(v, context="microdata", default_currency=cur.upper()) if v else None
            if c:
                res.candidates.append(c)
        # 3) site-specific hidden values — plain numbers in the page's display currency
        for sel in r.get("structured_inputs", []):
            try:
                v = page.css(sel).get()
            except Exception:
                v = None
            if v:
                c = parse_money(str(v), context=f"hidden input {sel} ({shown})", default_currency=shown)
                if c:
                    res.candidates.append(c)
        for pat in r.get("structured_regex", []):
            try:
                m = re.search(pat, src[:2_000_000])
            except re.error:
                continue
            if m:
                c = parse_money(m.group(1), context=f"embedded price data ({shown})", default_currency=shown)
                if c:
                    res.candidates.append(c)
    except Exception as e:  # never let one method break extraction
        res.error = f"{e.__class__.__name__}: {e}"
    return res