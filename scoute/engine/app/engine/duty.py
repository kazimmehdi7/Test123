"""Import duty estimate for a product title + origin + market."""
from __future__ import annotations

from .tables import load

EUR_USD = 1.09


def estimate(title: str, market: str = "US", sourcing: str = "china") -> dict:
    t = (title or "").lower()
    table = load("duty_rates")
    if sourcing == "us_warehouse":
        return {"mode": "included", "rate": 0.0, "low": 0.0, "high": 0.0, "flat_usd": 0.0, "hts": "—",
                "label": "Duty paid by the US warehouse supplier (included in their price)", "verified": False, "source": None}
    if market == "EU":
        flat = table["eu_flat_duty_eur_per_item"] * EUR_USD
        return {"mode": "flat", "rate": 0.0, "low": 0.0, "high": 0.0, "flat_usd": round(flat, 2), "hts": "—",
                "label": "EU flat duty per item (from 1 Jul 2026)", "verified": True, "source": None}
    rule = next((r for r in table["rules"] if any(k in t for k in r["keywords"])), table["default"])
    low, high = rule["china"] if sourcing == "china" else rule["other"]
    return {"mode": "ad_valorem", "rate": round((low + high) / 2, 4), "low": low, "high": high, "flat_usd": 0.0,
            "hts": rule["hts"], "label": rule["label"], "verified": bool(rule.get("verified")),
            "source": table.get("_sources", {}).get(rule.get("source", ""), None)}


def version() -> str:
    return load("duty_rates").get("_as_of", "")
