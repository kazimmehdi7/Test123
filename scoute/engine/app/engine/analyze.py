"""
Turn one marketplace listing + supplier candidates into a full opportunity:
True Profit (+ US-warehouse scenario), Failure Map, verdict, evidence.
"""
from __future__ import annotations

import time
from typing import Dict, List, Optional

from ..listing import Listing
from ..sources import risk
from ..sources.aliexpress import pack_qty
from . import duty, failure, launch, matching, profit, verdict
from .tables import load

DEFAULTS = {"ad_cost_pct": 0.20, "target_profit_pct": 0.15, "buffer_pct": 0.05, "us_warehouse_premium": 0.30}
RESELL_OUTBOUND_SHIP = 5.00   # estimate: you ship the item on to your buyer
MIN_MATCH = 0.5               # below this the supplier is probably a different product -> "Add supplier"
DEFAULT_SHIP = 4.00           # used only when the supplier listing shows no shipping cost — always disclosed


def build_inputs(sell_price: float, supplier_price: float, ship: float, category: str, title: str,
                 user: Dict, channel: str, market: str, sourcing: str, mode: str, overrides: Optional[Dict] = None) -> Dict:
    u = {**DEFAULTS, **(user or {})}
    d = duty.estimate(title, market, "domestic" if mode == "resell" else sourcing)
    if mode == "resell":
        d = {**d, "mode": "none", "rate": 0.0, "low": 0.0, "high": 0.0, "flat_usd": 0.0, "label": "Domestic purchase — no import duty"}
    supplier = supplier_price
    broker = 0.0
    if mode != "resell" and sourcing == "china" and market == "US":
        broker = load("duty_rates")["china_postal_fee_estimate_usd"]
    if mode != "resell" and sourcing == "us_warehouse":
        supplier = round(supplier_price * (1 + u["us_warehouse_premium"]), 2)
    if mode == "resell":
        ship = ship + RESELL_OUTBOUND_SHIP
    rr = load("return_rates")
    i = {"sell": sell_price, "supplier": supplier, "ship": ship, "duty_rate": d["rate"], "flat_duty": d["flat_usd"],
         "broker": broker, "channel": channel, "ad_pct": u["ad_cost_pct"] if mode != "resell" else 0.0,
         "return_rate": rr.get(category, rr["default"]), "buffer_pct": u["buffer_pct"],
         "target_pct": u["target_profit_pct"]}
    for k, v in (overrides or {}).items():
        if k in i and v is not None and v != "":
            i[k] = float(v) if k != "channel" else v
    return {"inputs": i, "duty": d}


def evaluate(inputs: Dict, confidence: float, match: float, rank, rank_before, blocked: bool) -> Dict:
    p = profit.compute(inputs)
    f = failure.analyse(inputs)
    v = verdict.decide(p, f, confidence, match, rank, rank_before, blocked)
    return {"profit": p, "failure": f, "verdict": v}


def why_today(sell: Listing) -> str:
    if sell.rank and sell.rank_before and sell.rank_before > sell.rank:
        return f"Sales rank {sell.rank_before} → {sell.rank} in the last 24 hours"
    if sell.rank:
        return f"#{sell.rank} in its category right now"
    if sell.review_count:
        return f"{sell.review_count:,} reviews — proven demand"
    return "Found in your search"


async def opportunity(sell: Listing, suppliers: List[Listing], category: str, user_settings: Dict,
                      mode: str = "dropship", market: str = "US", sourcing: str = "china", channel: str = "shopify",
                      demo: bool = False) -> Dict:
    r = risk.evaluate(sell.title, sell.brand)
    blocked = mode in ("dropship", "resell") and mode not in r["modes"]
    sup, match = matching.best(sell, suppliers)
    alternatives = [s.to_dict() for s in sorted(suppliers, key=lambda s: s.price or 999) if not sup or s.source_id != sup.source_id][:3]

    confidence = 0.4 + (0.15 if sell.price else 0) + (0.1 if sell.rating else 0) + (0.2 if sup and match >= 0.6 else 0)
    base = {
        "sell": sell.to_dict(), "supplier": sup.to_dict() if sup else None, "supplier_alternatives": alternatives,
        "match_confidence": match, "category": category, "mode": mode, "market": market, "sourcing": sourcing,
        "channel": channel, "risk": r, "why_today": why_today(sell), "is_demo": demo, "generated_at": time.time(),
        "duty_version": duty.version(),
        "affiliate": {"rate": load("affiliate_rates").get(category, load("affiliate_rates")["default"])},
    }
    base["affiliate"]["per_sale"] = round((sell.price or 0) * base["affiliate"]["rate"], 2)


    if blocked:  # brand/IP risk decides first: no supplier or price can make this dropshippable
        base.update(action=verdict.SKIP, confidence=round(min(confidence, 0.9), 2), inputs=None, duty=None, assumptions=[],
                    profit=None, profit_alt=None, failure=None,
                    verdict={"action": verdict.SKIP, "reasons": [r["reason"] or "Brand risk"]},
                    launch=launch.build(sell.title, {}), evidence=_evidence(sell, sup, demo))
        return base


    if not sell.price or not sup or match < MIN_MATCH:
        base.update(action=verdict.NO_MATCH, confidence=round(min(confidence, 0.5), 2), inputs=None, duty=None, assumptions=[],
                    profit=None, profit_us_warehouse=None, failure=None,
                    verdict={"action": verdict.NO_MATCH, "reasons": [
                        "No reliable supplier match yet" if sell.price else (
                            "Selling price couldn't be verified on the page, so it isn't used"
                            if sell.raw.get("price_status") == "unverified" else "Selling price not available"),
                        "Add your supplier's price to calculate the real profit"]},
                    launch=launch.build(sell.title, {}), evidence=_evidence(sell, None, demo))
        return base

    duty_info = duty.estimate(sell.title, market, sourcing)
    confidence += 0.1 if duty_info.get("verified") else 0

    # --- make the supplier cost comparable, and say out loud every assumption we make
    assumptions: List[str] = []
    sell_q = pack_qty(sell.title)
    sup_q = int(sup.raw.get("pack_qty") or pack_qty(sup.title)) or 1
    factor = sell_q / sup_q
    supplier_cost = round(sup.price * factor, 2)
    if factor != 1:
        assumptions.append(f"The marketplace listing is {sell_q} units and the supplier listing is {sup_q}, "
                           f"so supplier cost is ${sup.price:.2f} × {factor:g} = ${supplier_cost:.2f}.")
    if str(sup.raw.get("cost_basis", "")).startswith("original"):
        why = "new shoppers" if sup.raw.get("new_shopper_price") else "bundle purchases"
        assumptions.append(f"The supplier shows ${sup.raw.get('shown_price'):.2f}, but only for {why}. "
                           f"Repeat orders pay the regular ${sup.price:.2f}, which is what we use.")
    ship_known = sup.shipping_cost is not None
    ship = sup.shipping_cost if ship_known else DEFAULT_SHIP
    if not ship_known:
        confidence -= 0.1
        over = sup.raw.get("free_shipping_over")
        assumptions.append(f"Shipping isn't shown on the supplier listing, so we use a ${DEFAULT_SHIP:.2f} estimate"
                           + (f" (it's free only on orders over ${over:.2f})" if over else "")
                           + ". Check it on the supplier page and enter the real figure.")
    confidence = round(max(0.3, min(confidence, 0.95)), 2)

    built = build_inputs(sell.price, supplier_cost, ship,
                         category, sell.title, user_settings, channel, market, sourcing, mode)
    main = evaluate(built["inputs"], confidence, match, sell.rank, sell.rank_before, blocked)

    alt_scenario = None
    if mode != "resell" and market == "US":
        other = "us_warehouse" if sourcing == "china" else "china"
        b2 = build_inputs(sell.price, supplier_cost, ship,
                          category, sell.title, user_settings, channel, market, other, mode)
        alt_scenario = {"sourcing": other, **evaluate(b2["inputs"], confidence, match, sell.rank, sell.rank_before, blocked)["profit"]}

    if not ship_known:
        for line in main["profit"]["lines"]:
            if line["key"] == "ship":
                line["label"] = "Shipping to customer (estimate)"
    base["assumptions"] = assumptions
    base.update(action=main["verdict"]["action"], confidence=confidence, inputs=built["inputs"], duty=built["duty"],
                profit=main["profit"], profit_alt=alt_scenario, failure=main["failure"], verdict=main["verdict"],
                launch=launch.build(sell.title, main["profit"]), evidence=_evidence(sell, sup, demo))
    return base


def _evidence(sell: Listing, sup: Optional[Listing], demo: bool) -> List[Dict]:
    ev = [{"what": "Selling price, rating, rank", "source": sell.source, "url": sell.url, "fetched_at": sell.fetched_at,
           "demo": demo}]
    if sup:
        ev.append({"what": "Supplier price, shipping, orders", "source": sup.source, "url": sup.url,
                   "fetched_at": sup.fetched_at, "demo": demo})
    ev.append({"what": "Import duty", "source": "Scoute duty table (estimate)", "url": None, "fetched_at": None, "demo": False})
    ev.append({"what": "Platform fees, return rates", "source": "Scoute fee tables (estimate)", "url": None, "fetched_at": None, "demo": False})
    return ev


def rank_score(o: Dict) -> float:
    if not o.get("profit"):
        return -1.0
    w = {"HIGH": 1.0, "MEDIUM": 0.7, "LOW": 0.35}[o["failure"]["safety"]]
    mom = 1.3 if verdict.momentum_up(o["sell"].get("rank"), o["sell"].get("rank_before")) else 1.0
    return round(o["profit"]["net"] * w * mom * o["confidence"], 3)
