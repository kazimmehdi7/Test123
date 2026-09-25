"""Is this supplier listing the same physical product as the marketplace listing?"""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from ..listing import Listing

STOP = {"the", "and", "for", "with", "set", "pack", "of", "new", "hot", "sale", "free", "shipping", "pcs", "piece",
        "2024", "2025", "2026", "high", "quality", "best", "top", "1pc", "2pcs"}


def tokens(t: str) -> set:
    words = re.findall(r"[a-z]+", (t or "").lower())
    return {w[:-1] if w.endswith("s") and len(w) > 3 else w for w in words if len(w) > 2 and w not in STOP}


def score(sell: Listing, sup: Listing) -> float:
    a, b = tokens(sell.title), tokens(sup.title)
    if not a or not b:
        return 0.0
    overlap = len(a & b) / min(len(a), len(b))
    s = min(1.0, overlap)
    from ..sources.aliexpress import pack_qty
    sq, pq = pack_qty(sell.title), int(sup.raw.get("pack_qty") or pack_qty(sup.title)) or 1
    if sq != pq:
        s *= 0.85  # different pack size: still usable (cost gets scaled), but a same-size listing should win
    if sell.price and sup.price and (sup.price + (sup.shipping_cost or 0)) > sell.price * 0.85:
        s *= 0.5  # supplier this expensive is probably a different product or a reseller
    return round(s, 3)


def best(sell: Listing, candidates: List[Listing]) -> Tuple[Optional[Listing], float]:
    scored = sorted(((score(sell, c), c) for c in candidates if c.price), key=lambda x: (-x[0], x[1].price))
    if not scored:
        return None, 0.0
    top_score = scored[0][0]
    # among near-equal matches, prefer the cheaper landed one with more orders
    near = [c for s, c in scored if s >= top_score - 0.1]
    pick = min(near, key=lambda c: (c.price + (c.shipping_cost or 0)) - (c.sold_count or 0) / 1e6)
    return pick, score(sell, pick)
