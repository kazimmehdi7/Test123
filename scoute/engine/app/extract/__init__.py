"""
Price extraction with voting.

    result = await extract_price(page, "amazon", scope="product", title=title)
    if result.usable:
        price = result.price

Four methods each propose prices (their first proposal is their "vote"):
    structured (weight 3)  selectors (2)  patterns (1)  ai (2.5, only on disagreement)

    VERIFIED     two or more methods vote for the same price, and nothing strong disagrees
    LIKELY       one reliable method (structured/selectors) with no strong disagreement
    UNVERIFIED   methods disagree and nothing settles it -> price is NOT used
    UNAVAILABLE  the page says the item can't be bought
    NONE         no price found at all
Only VERIFIED and LIKELY prices are ever shown to users as real.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from . import ai_check, jsonld, patterns, selectors
from .common import Candidate, MethodResult, all_text, css, rules, same

WEIGHTS = {"structured": 3.0, "selectors": 2.0, "patterns": 1.0, "ai": 2.5}
RELIABLE = {"structured", "selectors"}
SECONDARY_SHARE = 0.4   # a method that lists a price but didn't vote for it gives partial support

VERIFIED, LIKELY, UNVERIFIED, UNAVAILABLE, NONE = "verified", "likely", "unverified", "unavailable", "none"


@dataclass
class PriceResult:
    status: str
    price: Optional[float] = None
    confidence: float = 0.0
    agreeing: List[str] = field(default_factory=list)
    methods: Dict[str, Any] = field(default_factory=dict)   # method -> its vote (or error) for logs
    reason: str = ""

    @property
    def usable(self) -> bool:
        return self.status in (VERIFIED, LIKELY) and self.price is not None

    def summary(self) -> Dict[str, Any]:
        return {"status": self.status, "price": self.price, "confidence": self.confidence,
                "agreeing": self.agreeing, "methods": self.methods, "reason": self.reason}


def _decide(results: List[MethodResult]) -> PriceResult:
    methods = {r.method: (round(r.primary.value, 2) if r.primary else (r.error or None)) for r in results}
    votes = [(r.method, r.primary) for r in results if r.primary]
    if not votes:
        return PriceResult(NONE, methods=methods, reason="No price found on the page")

    # cluster vote values
    clusters: List[List[Candidate]] = []
    for _, c in votes:
        for cl in clusters:
            if same(cl[0].value, c.value):
                cl.append(c)
                break
        else:
            clusters.append([c])

    def score(value: float) -> float:
        s = 0.0
        for r in results:
            if r.primary and same(r.primary.value, value):
                s += WEIGHTS[r.method]
            elif any(same(c.value, value) for c in r.candidates):
                s += WEIGHTS[r.method] * SECONDARY_SHARE
        return s

    ranked = sorted(clusters, key=lambda cl: score(cl[0].value), reverse=True)
    best = ranked[0][0].value
    s1 = score(best)
    s2 = score(ranked[1][0].value) if len(ranked) > 1 else 0.0
    agreeing = [m for m, c in votes if same(c.value, best)]
    strong_disagree = s2 > 0 and s2 >= s1 * 0.5

    if len(agreeing) >= 2 and not strong_disagree:
        return PriceResult(VERIFIED, round(best, 2), 0.95, agreeing, methods, f"{', '.join(agreeing)} agree")
    if len(agreeing) == 1 and agreeing[0] in RELIABLE | {"ai"} and not strong_disagree:
        return PriceResult(LIKELY, round(best, 2), 0.75, agreeing, methods, f"only {agreeing[0]} found a price")
    if len(agreeing) >= 2 and strong_disagree and s1 >= s2 * 1.5:
        return PriceResult(LIKELY, round(best, 2), 0.7, agreeing, methods, "majority wins over a weaker conflicting price")
    others = sorted({round(cl[0].value, 2) for cl in ranked})
    return PriceResult(UNVERIFIED, None, 0.3, agreeing, methods, f"methods disagree: {others}")


def _unavailable(page: Any, site: str) -> bool:
    r = rules(site)
    for sel in r.get("availability_zone", []):
        for el in css(page, sel)[:1]:
            t = all_text(el, 600).lower()
            if any(m in t for m in r.get("unavailable_markers", [])):
                return True
    return False


async def extract_price(page: Any, site: str, scope: str = "product", title: str = "", use_ai: bool = True) -> PriceResult:
    """scope='product' runs all methods (and AI on disagreement). 'card'/'movers' run selectors + patterns only."""
    if scope == "product":
        results = [jsonld.extract(page, site), selectors.extract(page, site, "product"), patterns.extract(page, site, "product")]
    else:
        results = [selectors.extract(page, site, scope), patterns.extract(page, site, scope)]
    decision = _decide(results)

    if decision.status == UNVERIFIED and scope == "product" and use_ai:
        zone = " ".join(all_text(z, 800) for sel in rules(site).get("price_zones", []) for z in css(page, sel)[:1])
        pool = [c for r in results for c in r.candidates]
        ai = await ai_check.extract(title, pool, zone)
        results.append(ai)
        if ai.primary:
            decision = _decide(results)
        else:
            decision.methods["ai"] = ai.error

    if decision.status in (NONE, UNVERIFIED) and scope == "product" and _unavailable(page, site):
        decision.status, decision.price, decision.reason = UNAVAILABLE, None, "Page says the item can't be bought right now"
    return decision


def extract_card_price(card: Any, site: str, scope: str = "card") -> PriceResult:
    """Synchronous version for search-result cards and best-seller tiles (no AI, no JSON-LD)."""
    return _decide([selectors.extract(card, site, scope), patterns.extract(card, site, scope)])
