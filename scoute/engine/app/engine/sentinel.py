"""
Autonomous Margin Sentinel & Competitor Saturation Engine.
Evaluates real-time threats across:
1. Competitor saturation & active ad pressure (Saturation Index 0-100)
2. Ad acquisition headroom & Maximum Allowable CPA (CPA_max)
3. Supplier freight & price drift
4. Actionable tactical defense recommendations
"""
from __future__ import annotations

import hashlib
import random
from datetime import date
from typing import Dict, List, Optional, Tuple
from .profit import compute
from .failure import analyse


def calculate_saturation_index(
    competitor_count: int,
    active_ads_count: int,
    review_velocity_monthly: int = 150
) -> Dict:
    """
    Computes Saturation Index (0 - 100) and saturation stage.
    """
    # Base saturation from competing stores
    store_factor = min(40.0, competitor_count * 2.5)
    # Ad pressure from active creative campaigns
    ad_factor = min(40.0, active_ads_count * 3.0)
    # Market review maturity
    velocity_factor = min(20.0, (review_velocity_monthly / 50.0) * 5.0)

    score = round(min(100.0, max(0.0, store_factor + ad_factor + velocity_factor)), 1)

    if score < 25:
        stage = "UNTAPPED"
        label = "Low Competition / Blue Ocean"
        description = "Few active advertisers. Low CPMs and high ad conversion expected."
    elif score < 55:
        stage = "GROWING"
        label = "Moderate Competition / Scaling Phase"
        description = "Market is actively expanding with healthy customer demand."
    elif score < 80:
        stage = "COMPETITIVE"
        label = "High Competition / Saturated Ads"
        description = "Multiple active stores running ads. Require unique hooks or bundle pricing."
    else:
        stage = "SATURATED"
        label = "Heavily Saturated / Price War"
        description = "High ad fatigue and intense CPC bidding wars. Margin compression risk."

    return {
        "score": score,
        "stage": stage,
        "label": label,
        "description": description,
        "competitor_count": competitor_count,
        "active_ads_count": active_ads_count,
    }


def _seed(*parts) -> random.Random:
    h = hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()
    return random.Random(int(h[:12], 16))


def simulate_competition_drift(seed_key: str, day: date, base_competitors: int, base_ads: int) -> Tuple[int, int]:
    """
    Day-seeded, bounded competitor/ad-count estimate anchored to a fixed base.

    IMPORTANT — this is a heuristic placeholder, not live data: Scoute does not integrate
    with the Meta/TikTok ad library or scrape competing storefronts, so there is no real
    "competitor radar" feed. Earlier this function's caller simply added +1 competitor and
    +2 ads on every scan, which made every monitored product march toward CRITICAL/SATURATED
    over time regardless of the real market — a one-way ratchet, not a signal. This version
    instead produces a deterministic, bounded fluctuation around the count recorded when the
    product was first tracked, so repeated scans don't manufacture threat on their own.
    Replace with a real competitor/ad-spend integration before relying on this for launch
    decisions (see README "Before launch — verify these by hand").
    """
    r = _seed(seed_key, day.isoformat())
    competitors = max(0, round(base_competitors * (1 + r.uniform(-0.25, 0.45))))
    active_ads = max(0, round(base_ads * (1 + r.uniform(-0.30, 0.55))))
    return competitors, active_ads


def analyze_sentinel_health(
    inputs: Dict,
    saturation: Dict,
    current_estimated_cpa: Optional[float] = None,
    supplier_status: str = "STABLE"
) -> Dict:
    """
    Evaluates unit economics under active market conditions and computes
    threat level, ad headroom, and tactical recommendations.
    """
    profit_data = compute(inputs)
    failure_data = analyse(inputs)

    retail = profit_data["sell"]
    net_profit = profit_data["net"]
    target_profit = profit_data["target"]
    max_cpa = profit_data["max_ad_per_sale"]

    # Current CPA estimate based on saturation if not provided
    if current_estimated_cpa is None:
        # Base CPA scales from 15% of retail (low saturation) to 35%+ of retail (high saturation)
        base_pct = 0.15 + (saturation["score"] / 100.0) * 0.20
        cpa_est = round(retail * base_pct, 2)
    else:
        cpa_est = round(float(current_estimated_cpa), 2)

    cpa_headroom = round(max_cpa - cpa_est, 2)

    # Determine Threat Level
    reasons: List[str] = []
    recommendations: List[str] = []

    if net_profit <= 0:
        threat_level = "CRITICAL"
        reasons.append(f"Unit net profit is negative (${abs(net_profit):.2f}/unit loss).")
        recommendations.append(f"Immediate Action: Pause ad campaigns or increase retail price to at least ${profit_data['landed'] + profit_data['fees'] + 10:.2f}.")
    elif cpa_headroom < 0:
        threat_level = "CRITICAL"
        reasons.append(f"Estimated CPA (${cpa_est:.2f}) exceeds Max Allowable CPA (${max_cpa:.2f}) by ${abs(cpa_headroom):.2f}.")
        recommendations.append(f"Cap your ad platform target acquisition cost strictly at ${max_cpa:.2f}.")
        recommendations.append(f"Test new creative angles or bundle offers to lift average order value.")
    elif failure_data["safety"] == "LOW" or saturation["stage"] in ("COMPETITIVE", "SATURATED"):
        threat_level = "WARNING"
        if saturation["stage"] in ("COMPETITIVE", "SATURATED"):
            reasons.append(f"High ad saturation ({saturation['score']}/100) increasing customer acquisition costs.")
            recommendations.append("Differentiate listing with custom video hooks and expedited 3-5 day shipping.")
        if failure_data["safety"] == "LOW":
            reasons.append("Safety margin is low. Less than 10% room before zero profitability.")
            recommendations.append(f"Negotiate supplier pricing down from ${profit_data['supplier']:.2f} to ${profit_data['max_buy_price']:.2f}.")
    elif net_profit >= target_profit and cpa_headroom >= 4.0:
        threat_level = "THRIVING"
        reasons.append(f"Strong profitability (${net_profit:.2f}/unit) with healthy CPA headroom (+${cpa_headroom:.2f}).")
        recommendations.append("Scale ad spend aggressively across Meta, TikTok, and Google Shopping.")
        recommendations.append("Consider ordering bulk inventory to US 3PL warehouse to cut unit costs by ~25%.")
    else:
        threat_level = "STABLE"
        reasons.append(f"Unit economics are steady at ${net_profit:.2f} net keep per sale.")
        recommendations.append(f"Maintain ad spend with target CPA at or below ${max_cpa:.2f}.")

    if supplier_status != "STABLE":
        threat_level = "WARNING" if threat_level != "CRITICAL" else threat_level
        reasons.append(f"Supplier alert: {supplier_status.replace('_', ' ').title()}")
        recommendations.append("Check supplier backup candidate to secure fulfillment continuity.")

    return {
        "threat_level": threat_level,
        "net_profit": net_profit,
        "margin": profit_data["margin"],
        "max_allowable_cpa": max_cpa,
        "current_estimated_cpa": cpa_est,
        "cpa_headroom": cpa_headroom,
        "safety_level": failure_data["safety"],
        "saturation": saturation,
        "supplier_status": supplier_status,
        "reasons": reasons[:3],
        "recommendations": recommendations[:3],
        "profit_breakdown": profit_data,
    }
