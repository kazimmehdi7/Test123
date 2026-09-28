"""
Multi-Signal Product Matching Engine.
Compares a marketplace listing against supplier candidates using:
1. Canonical entity & core product noun cluster alignment
2. Material & specification consistency
3. Dimension / size compatibility
4. Pack count normalization
5. Realistic landed price feasibility
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple

from ..listing import Listing
from .entity import extract_entity, ProductEntity

STOP = {
    "the", "and", "for", "with", "set", "pack", "of", "new", "hot", "sale", "free",
    "shipping", "pcs", "piece", "pieces", "2024", "2025", "2026", "high", "quality",
    "best", "top", "1pc", "2pcs", "3pcs", "4pcs", "5pcs", "6pcs", "item", "home",
    "kitchen", "tool", "tools", "accessories", "gadget", "gadgets", "product", "easy",
    "reusable", "durable", "resistant", "clean"
}


def _stem(w: str) -> str:
    return w[:-1] if (w.endswith("s") and len(w) > 3 and not w.endswith("ss")) else w


def _clean_tokens(text: str) -> Set[str]:
    """Tokenize and stem basic plurals."""
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {_stem(w) for w in words if len(w) > 2 and w not in STOP}


def _head_noun(title: str) -> Optional[str]:
    """The last significant word of a cleaned title, stemmed — a cheap general proxy for the
    core product noun (English product titles overwhelmingly end in it: 'Resistance Bands
    Set', 'Desk Mat Leather', 'Baby Nail Trimmer'). Used as a fallback signal when neither
    title matched the curated NOUN_CLUSTERS dictionary, since that dictionary can't cover
    every category — without this, two completely different products with no cluster hit
    scored a neutral 1.0 with zero mismatch protection."""
    ordered = [_stem(w) for w in re.findall(r"[a-z0-9]+", (title or "").lower())
               if len(w) > 2 and w not in STOP]
    return ordered[-1] if ordered else None


def _ngram_similarity(s1: str, s2: str, n: int = 3) -> float:
    """Character n-gram similarity for fuzzy matching between short phrases."""
    s1, s2 = (s1 or "").lower().strip(), (s2 or "").lower().strip()
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0
    ngrams1 = {s1[i:i+n] for i in range(len(s1) - n + 1)} or {s1}
    ngrams2 = {s2[i:i+n] for i in range(len(s2) - n + 1)} or {s2}
    intersection = len(ngrams1 & ngrams2)
    union = len(ngrams1 | ngrams2)
    return intersection / union if union else 0.0


def score(sell: Listing, sup: Listing, sell_entity: Optional[ProductEntity] = None) -> float:
    """
    Calculate a multi-signal match confidence score [0.0 - 1.0] between a marketplace
    listing and a supplier candidate.
    """
    if not sell.title or not sup.title:
        return 0.0

    if sell_entity is None:
        sell_entity = extract_entity(sell.title)
    sup_entity = extract_entity(sup.title)

    # 1. Core Noun Cluster Compatibility
    cluster_score = 1.0
    if sell_entity.noun_cluster and sup_entity.noun_cluster:
        if sell_entity.noun_cluster != sup_entity.noun_cluster:
            # Different core product type (e.g. mat vs spatula or knife vs board)
            cluster_score = 0.30
        else:
            # Confirmed same core product type
            cluster_score = 1.30
    elif sell_entity.noun_cluster or sup_entity.noun_cluster:
        # One has a defined cluster, check if cluster keywords appear in the other
        target_cluster = sell_entity.noun_cluster or sup_entity.noun_cluster
        from .entity import NOUN_CLUSTERS
        cluster_words = NOUN_CLUSTERS.get(target_cluster, set())
        other_title = sup.title.lower() if sell_entity.noun_cluster else sell.title.lower()
        if any(w in other_title for w in cluster_words):
            cluster_score = 1.20
        else:
            cluster_score = 0.65
    else:
        # Neither title matched the curated NOUN_CLUSTERS dictionary — common for categories
        # it doesn't cover — which used to leave cluster_score at a neutral 1.0, i.e. zero
        # mismatch protection for whole categories. Fall back to comparing the head noun (last
        # significant word) of each title: a general, dictionary-free product-type signal.
        h1, h2 = _head_noun(sell.title), _head_noun(sup.title)
        if h1 and h2:
            if h1 == h2:
                cluster_score = 1.15
            elif _ngram_similarity(h1, h2) >= 0.6:
                cluster_score = 0.95  # likely the same word, different plural/spelling
            else:
                cluster_score = 0.55  # probably a different product type

    # 2. Token Overlap on informative descriptors
    a_tokens = _clean_tokens(sell.title)
    b_tokens = _clean_tokens(sup.title)
    if not a_tokens or not b_tokens:
        return 0.0

    common = a_tokens & b_tokens
    # Balanced Jaccard & Coverage
    jaccard = len(common) / (len(a_tokens | b_tokens) or 1)
    coverage = len(common) / (min(len(a_tokens), len(b_tokens)) or 1)
    text_score = 0.40 * jaccard + 0.60 * coverage

    # 3. Material consistency check
    mat_score = 1.0
    if sell_entity.material:
        if sup_entity.material:
            if sell_entity.material != sup_entity.material:
                mat_score = 0.35  # Conflicting materials (e.g. silicone vs wood)
            else:
                mat_score = 1.20 # Confirmed matching material
        else:
            if sell_entity.material in sup.title.lower():
                mat_score = 1.15
            else:
                mat_score = 0.80 # Unmentioned material

    # 4. Dimension / Spec matching
    spec_score = 1.0
    if sell_entity.dimensions and sup_entity.dimensions:
        match_dim = any(
            _ngram_similarity(d1, d2) >= 0.65
            for d1 in sell_entity.dimensions
            for d2 in sup_entity.dimensions
        )
        if match_dim:
            spec_score = 1.20
        else:
            spec_score = 0.85

    # 5. Pack Quantity alignment
    sq, pq = sell_entity.pack_qty, sup_entity.pack_qty
    pack_factor = 1.0
    if sq != pq:
        pack_factor = 0.90 # slight discount for different pack count (cost gets scaled in analyze)

    # 6. Price & Economic Feasibility Safeguards — compared on a pack-size-normalized basis.
    # A supplier listing priced for a bulk lot (e.g. a 10-pack) can't be compared directly
    # against a sell listing's price for its own pack size (e.g. a 2-pack): $25 for a 10-pack
    # looks like a "reseller" red flag next to a $19.99 2-pack sell price, even though the
    # real per-2-unit cost is $5. This used to compare raw, unscaled prices, so a bulk-lot
    # listing could be wrongly rejected (or a mismatched pack size wrongly accepted) before
    # engine.analyze ever gets a chance to scale it correctly.
    price_factor = 1.0
    if sell.price and sup.price:
        unit_ratio = (sq / pq) if pq else 1.0
        landed_estimate = sup.price * unit_ratio + (sup.shipping_cost or 0.0)
        # Reseller flag: supplier price exceeds 85% of retail selling price
        if landed_estimate > sell.price * 0.85:
            price_factor = 0.45
        # Teaser / Sample flag: supplier price is under 3% of retail on items over $15
        elif landed_estimate < sell.price * 0.03 and sell.price >= 15.0:
            price_factor = 0.30
        # Typical wholesale margin band (10% - 60% of retail price)
        elif 0.10 * sell.price <= landed_estimate <= 0.60 * sell.price:
            price_factor = 1.10

    final_score = text_score * cluster_score * mat_score * spec_score * pack_factor * price_factor
    return round(max(0.0, min(1.0, final_score)), 3)


def best(sell: Listing, candidates: List[Listing]) -> Tuple[Optional[Listing], float]:
    """
    Select the highest-quality matching supplier listing from candidate list.
    Prioritizes match confidence score, rating, order count, and competitive landed price.
    """
    valid_candidates = [c for c in candidates if c.price and c.price > 0]
    if not valid_candidates:
        return None, 0.0

    sell_entity = extract_entity(sell.title)
    scored = [(score(sell, c, sell_entity), c) for c in valid_candidates]
    scored.sort(key=lambda x: (-x[0], x[1].price))

    top_score = scored[0][0]
    if top_score <= 0.0:
        return None, 0.0

    # Among strong matches within 0.10 of top score, pick the one with best reliability & price
    near = [c for s, c in scored if s >= top_score - 0.10 and s >= 0.40]
    if not near:
        near = [scored[0][1]]

    def _unit_landed(c: Listing) -> float:
        # Same pack-size normalization as the price-feasibility check in score() — comparing
        # raw prices here would let a bulk-lot listing "win" the tie-break purely for looking
        # cheap per-listing, when it's actually priced for the wrong quantity.
        pq = extract_entity(c.title).pack_qty or 1
        ratio = sell_entity.pack_qty / pq
        return c.price * ratio + (c.shipping_cost or 0.0)

    pick = min(
        near,
        key=lambda c: _unit_landed(c) - ((c.rating or 4.0) * 0.5) - ((c.sold_count or 0) / 100_000)
    )

    final_score = score(sell, pick, sell_entity)
    return pick, final_score
