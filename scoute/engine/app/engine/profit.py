"""
True Profit: per-unit net profit after every cost, plus the reverse numbers
(max supplier price, max ad cost per sale). Pure functions — no network.

Net = sell - (supplier*(1+duty) + ship + broker + flat_duty) - channel_fee
          - ad_cost - returns - buffer
"""
from __future__ import annotations

from typing import Dict

from .tables import load


def channel_fee(channel: str, sell: float) -> float:
    f = load("channel_fees").get(channel) or load("channel_fees")["amazon"]
    return round(max(sell * f["pct"] + f["fixed"], f["min_fee"]), 2)


def compute(i: Dict) -> Dict:
    """i: sell, supplier, ship, duty_rate, flat_duty, broker, channel, ad_pct, return_rate, buffer_pct, target_pct"""
    sell = float(i["sell"])
    duty = round(i["supplier"] * i["duty_rate"] + i.get("flat_duty", 0.0), 2)
    landed = round(i["supplier"] + i["ship"] + duty + i["broker"], 2)
    fees = channel_fee(i["channel"], sell)
    ads = round(sell * i["ad_pct"], 2)
    returns = round(sell * i["return_rate"], 2)
    buffer = round(sell * i["buffer_pct"], 2)
    net = round(sell - landed - fees - ads - returns - buffer, 2)
    target = round(sell * i["target_pct"], 2)

    fixed_ex_supplier = i["ship"] + i["broker"] + i.get("flat_duty", 0.0) + fees + ads + returns + buffer
    max_buy = round((sell - fixed_ex_supplier - target) / (1 + i["duty_rate"]), 2)
    max_ads = round(sell - landed - fees - returns - buffer - target, 2)

    return {
        "sell": sell, "supplier": round(i["supplier"], 2), "ship": round(i["ship"], 2), "duty": duty,
        "broker": round(i["broker"], 2), "landed": landed, "fees": fees, "ads": ads, "returns": returns,
        "buffer": buffer, "net": net, "margin": round(net / sell, 4) if sell else 0.0, "target": target,
        "max_buy_price": max_buy, "max_ad_per_sale": max_ads,
        "lines": [
            {"key": "sell",     "label": "Selling price",            "amount": sell},
            {"key": "supplier", "label": "Supplier price",           "amount": -round(i["supplier"], 2)},
            {"key": "ship",     "label": "Shipping to customer",     "amount": -round(i["ship"], 2)},
            {"key": "duty",     "label": "Import duty (estimate)",   "amount": -duty},
            {"key": "broker",   "label": "Customs / postal fee",     "amount": -round(i["broker"], 2)},
            {"key": "fees",     "label": "Platform fees",            "amount": -fees},
            {"key": "ads",      "label": "Ad cost per sale",         "amount": -ads},
            {"key": "returns",  "label": "Returns allowance",        "amount": -returns},
            {"key": "buffer",   "label": "Uncertainty buffer",       "amount": -buffer},
        ],
    }


def breakeven_units(net: float, budget: float) -> int | None:
    """Units needed to earn back a test budget (ads + samples)."""
    if net <= 0 or not budget:
        return None
    return int(-(-budget // net))
