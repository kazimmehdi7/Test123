"""One shape for every marketplace and supplier listing."""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional

SELL, SUPPLY = "sell", "supply"


@dataclass
class Listing:
    source: str
    side: str
    source_id: str
    title: str
    url: str
    price: Optional[float] = None
    price_max: Optional[float] = None
    original_currency: str = "USD"
    brand: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    sold_count: Optional[int] = None
    shipping_cost: Optional[float] = None
    shipping_days: Optional[str] = None
    is_sponsored: bool = False
    has_prime: bool = False
    image_url: Optional[str] = None
    affiliate_url: Optional[str] = None
    rank: Optional[int] = None
    rank_before: Optional[int] = None
    confidence: float = 0.5
    raw: Dict[str, Any] = field(default_factory=dict)
    fetched_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Listing":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
