"""
Method 3 — currency amounts in the page text, closest to where you buy.
Looks inside the buy box / price zones first; skips list prices, unit prices,
shipping, coupons (see NOT_THE_PRICE in common.py).
"""
from __future__ import annotations

from typing import Any

from .common import MethodResult, all_text, css, money_in_text, rules


def extract(node: Any, site: str, scope: str = "product") -> MethodResult:
    res = MethodResult("patterns")
    try:
        if scope == "product":
            r = rules(site)
            zones = []
            for sel in r.get("price_zones", []) + r.get("buy_anchors", []):
                zones += css(node, sel)[:1]
            seen = set()
            for z in zones:
                for c in money_in_text(all_text(z, 3000)):
                    if round(c.value, 2) not in seen:
                        seen.add(round(c.value, 2))
                        res.candidates.append(c)
        else:
            res.candidates = money_in_text(all_text(node, 1500))[:5]
    except Exception as e:
        res.error = f"{e.__class__.__name__}: {e}"
    return res
