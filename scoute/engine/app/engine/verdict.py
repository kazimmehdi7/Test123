"""SOURCE / SOURCE SMALL / WAIT / SKIP from the numbers — no hidden score."""
from __future__ import annotations

from typing import Dict, List, Optional

SOURCE, SMALL, WAIT, SKIP, NO_MATCH = "SOURCE", "SOURCE_SMALL", "WAIT", "SKIP", "NO_MATCH"


def momentum_up(rank: Optional[int], before: Optional[int]) -> bool:
    return bool(rank and before and before / rank >= 1.5)


def decide(profit: Dict, failure: Dict, confidence: float, match: float, rank: Optional[int],
           rank_before: Optional[int], blocked: bool) -> Dict:
    reasons: List[str] = []
    net, target, safety = profit["net"], profit["target"], failure["safety"]
    up = momentum_up(rank, rank_before)

    if blocked:
        return {"action": SKIP, "reasons": ["Major brand: trademark risk for dropshipping and reselling. Affiliate only."]}
    if net <= 0:
        action = SKIP
        reasons.append(f"Loses ${abs(net):.2f} per sale after all costs")
    elif net >= target and safety in ("HIGH", "MEDIUM"):
        action = SOURCE if confidence >= 0.7 and match >= 0.75 else SMALL
        reasons.append(f"Keeps ${net:.2f} per sale, above your ${target:.2f} target")
        if action == SMALL:
            reasons.append("Supplier match or data is not certain yet — verify the supplier before a big order")
    else:
        action = WAIT if up else SKIP
        if net < target:
            reasons.append(f"Keeps ${net:.2f} per sale, below your ${target:.2f} target")
        if safety == "LOW":
            reasons.append("Very little room before it stops making money")
    if up:
        reasons.append(f"Sales rank moved {rank_before} → {rank} in the last 24h")
    elif rank:
        reasons.append(f"Current sales rank in category: #{rank}")
    return {"action": action, "reasons": reasons[:3]}
