"""
Failure Map: for each variable, the value where profit hits zero (others held),
how far that is from today, and how much profit drops if it gets 10% worse.
"""
from __future__ import annotations

from typing import Callable, Dict, List

from .profit import compute

VARS = [
    # key, label, direction ('down' = danger when it falls), how to render
    ("sell",        "Selling price",    "down", "money"),
    ("supplier",    "Supplier price",   "up",   "money"),
    ("ad_pct",      "Ad cost per sale", "up",   "pct_of_sell"),
    ("duty_rate",   "Import duty rate", "up",   "pct"),
    ("return_rate", "Return rate",      "up",   "pct"),
]


def _solve(f: Callable[[float], float], lo: float, hi: float) -> float | None:
    flo, fhi = f(lo), f(hi)
    if flo == 0:
        return lo
    if (flo > 0) == (fhi > 0):
        return None
    for _ in range(60):
        mid = (lo + hi) / 2
        if (f(mid) > 0) == (flo > 0):
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def analyse(inputs: Dict) -> Dict:
    base = compute(inputs)
    net0 = base["net"]
    points: List[Dict] = []
    for key, label, direction, kind in VARS:
        cur = float(inputs[key])
        net_at = lambda v, k=key: compute({**inputs, k: v})["net"]
        if direction == "down":
            bp = _solve(net_at, 0.0, max(cur, 0.01)) if net0 > 0 else cur
        else:
            ceiling = max(cur * 10, 1.0 if kind in ("pct", "pct_of_sell") else cur * 10 + 50)
            bp = _solve(net_at, cur, ceiling) if net0 > 0 else cur
        if bp is None:
            distance = None
        elif cur == 0:
            distance = bp  # absolute points for rates starting at 0
        else:
            distance = abs(bp - cur) / cur
        worse = cur * (0.9 if direction == "down" else 1.1) if cur else (0.10 if direction == "up" else 0)
        drop = None
        if net0 > 0:
            drop = round((net0 - compute({**inputs, key: worse})["net"]) / net0, 3)
        points.append({"key": key, "label": label, "kind": kind, "current": round(cur, 4),
                       "break_point": round(bp, 4) if bp is not None else None,
                       "distance": round(distance, 4) if distance is not None else None,
                       "drop_if_10pct_worse": drop, "direction": direction})

    key_distances = [p["distance"] for p in points if p["key"] in ("sell", "supplier", "ad_pct") and p["distance"] is not None]
    nearest = min(key_distances) if key_distances and net0 > 0 else 0.0
    safety = "HIGH" if nearest >= 0.25 else "MEDIUM" if nearest >= 0.10 else "LOW"
    risks = sorted([p for p in points if p["drop_if_10pct_worse"]], key=lambda p: p["drop_if_10pct_worse"], reverse=True)[:3]
    return {"safety": safety, "nearest_distance": round(nearest, 4), "points": points,
            "biggest_risks": [{"label": p["label"], "drop": p["drop_if_10pct_worse"]} for p in risks]}
