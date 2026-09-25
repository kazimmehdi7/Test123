"""Brand / IP gate. Major brands can't be dropshipped or resold safely; affiliate is fine."""
from __future__ import annotations

import re
from typing import Optional

MAJOR_BRANDS = {
    "apple", "samsung", "sony", "microsoft", "google", "amazon", "bose", "dyson", "philips", "panasonic", "canon",
    "nikon", "dell", "hp", "lenovo", "asus", "acer", "razer", "logitech", "jbl", "sennheiser", "beats", "gopro",
    "fitbit", "yeti", "hydro flask", "hydroflask", "stanley", "contigo", "nalgene", "owala", "thermos", "camelbak",
    "nike", "adidas", "puma", "gucci", "louis vuitton", "chanel", "rolex", "under armour", "north face", "supreme",
    "lululemon", "patagonia", "columbia", "kitchenaid", "cuisinart", "instant pot", "ninja", "vitamix", "breville",
    "keurig", "nespresso", "lego", "disney", "3m", "pampers", "huggies", "kong", "olaplex", "cerave", "the ordinary",
}
RESTRICTED = {"weapon", "firearm", "ammunition", "knife set", "drug", "medication", "prescription", "alcohol",
              "tobacco", "vape", "e-cigarette", "adult", "casino", "supplement"}
ACCESSORY = {"case for", "cover for", "compatible with", "replacement for", "for iphone", "for samsung", "fits "}


def evaluate(title: str, brand: Optional[str] = None) -> dict:
    t = (title or "").lower()
    b = (brand or "").lower()
    for r in RESTRICTED:
        if r in t:
            return {"level": "blocked", "modes": [], "reason": f"Restricted category ({r}) — needs approval or licenses"}
    is_accessory = any(a in t for a in ACCESSORY)
    for brand_name in sorted(MAJOR_BRANDS, key=len, reverse=True):
        pattern = rf"\b{re.escape(brand_name)}\b"
        if re.search(pattern, t) or re.search(pattern, b):
            if is_accessory and brand_name not in b:
                return {"level": "low", "modes": ["dropship", "resell", "affiliate"],
                        "reason": f"Accessory for {brand_name.title()} — fine if you don't use their logo"}
            return {"level": "brand", "modes": ["affiliate"],
                    "reason": f"{brand_name.title()} is a major brand — trademark risk for dropship/resell. Affiliate only."}
    return {"level": "none", "modes": ["dropship", "resell", "affiliate"], "reason": None}
