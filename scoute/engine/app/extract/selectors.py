"""
Method 2 — the site's own price elements, from data/selectors.json.
Handles Amazon's split price ("14." + "99") and skips strike-through list prices
(they carry .a-text-price, excluded in the selectors themselves).
"""
from __future__ import annotations

from typing import Any

from .common import MethodResult, css, css_first_text, parse_money, rules


def _split_price(node: Any) -> str | None:
    whole = css_first_text(node, ".a-price-whole::text")
    if not whole:
        return None
    frac = (css_first_text(node, ".a-price-fraction::text") or "00").strip()
    sym = css_first_text(node, ".a-price-symbol::text") or "$"
    return f"{sym}{whole.strip().rstrip('.').rstrip(',')}.{frac}"


def extract(node: Any, site: str, scope: str = "product") -> MethodResult:
    """scope: 'product' (a product page), 'card' (a search result), 'movers' (a best-seller tile)."""
    res = MethodResult("selectors")
    try:
        r = rules(site)
        key = {"product": "product_price", "card": "card_price", "movers": "movers_price"}[scope]
        split_key = {"product": "product_split_scopes", "card": "card_split_scopes", "movers": "card_split_scopes"}[scope]
        for sel in r.get(key, []):
            for el in css(node, sel)[:3]:
                text = css_first_text(el, "::text") or ""
                c = parse_money(text, context=f"{sel}")
                if c and all(abs(c.value - x.value) > 0.001 for x in res.candidates):
                    res.candidates.append(c)
        for sel in r.get(split_key, []):
            for el in css(node, sel)[:3]:
                text = _split_price(el)
                c = parse_money(text or "", context=f"split {sel}")
                if c and all(abs(c.value - x.value) > 0.001 for x in res.candidates):
                    res.candidates.append(c)
    except Exception as e:
        res.error = f"{e.__class__.__name__}: {e}"
    return res
