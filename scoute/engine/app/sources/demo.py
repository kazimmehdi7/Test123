"""
DEMO data (SCOUTE_DEMO=true). Lets you click through the whole product without
scraping. Every row made from here is stored with is_demo=True and the UI shows
a 'Demo data' banner. Never enable in production.
"""
from __future__ import annotations

import hashlib
import random
from datetime import date
from typing import Dict, List

from ..listing import SELL, SUPPLY, Listing

# category -> [(title, sell price, rating, reviews, rank, rank_before, supplier price, ship, sold, ship days)]
CATALOG: Dict[str, list] = {
    "kitchen": [
        ("Silicone Baking Mat Set of 2, Non-Stick Half Sheet Liner", 19.99, 4.7, 8421, 14, 61, 3.20, 2.10, 2000, "9-14 days"),
        ("Magnetic Knife Strip 16 Inch Stainless Steel Holder", 24.99, 4.6, 3120, 22, 70, 6.80, 3.40, 850, "10-15 days"),
        ("Collapsible Silicone Food Storage Containers 4-Pack", 29.99, 4.4, 1980, 37, 88, 9.90, 4.20, 610, "12-18 days"),
    ],
    "home": [
        ("Under Sink Organizer 2-Tier Sliding Shelf", 32.99, 4.5, 5210, 9, 44, 10.40, 5.10, 1300, "10-16 days"),
        ("Motion Sensor Closet Light Rechargeable 3-Pack", 22.99, 4.4, 6720, 18, 53, 5.60, 1.80, 4200, "8-13 days"),
        ("Linen Throw Pillow Covers 18x18 Set of 4", 21.99, 4.6, 2890, 41, 97, 7.10, 3.00, 980, "11-17 days"),
    ],
    "pet": [
        ("Lick Mat for Dogs with Suction Cups 2-Pack", 14.99, 4.7, 12040, 6, 29, 2.40, 1.50, 5400, "9-14 days"),
        ("Cat Window Perch Hammock with Strong Suction", 27.99, 4.5, 4480, 15, 58, 7.90, 4.60, 1700, "12-18 days"),
        ("No Pull Dog Harness Reflective Adjustable", 25.99, 4.6, 9310, 24, 36, 6.20, 2.20, 3100, "10-15 days"),
    ],
    "beauty": [
        ("Heatless Hair Curler Silk Rod Headband Set", 16.99, 4.4, 15600, 5, 33, 2.10, 1.20, 9800, "8-12 days"),
        ("Gua Sha Facial Tool Stainless Steel", 18.99, 4.5, 3470, 27, 81, 3.60, 1.60, 2200, "9-14 days"),
        ("Makeup Brush Cleaner Mat Silicone", 11.99, 4.3, 2250, 49, 90, 1.30, 1.10, 3600, "9-14 days"),
    ],
    "fitness": [
        ("Resistance Bands Set with Handles 11 Piece", 29.99, 4.6, 21030, 11, 39, 7.40, 3.90, 6100, "10-15 days"),
        ("Weighted Jump Rope Cordless Counter", 21.99, 4.4, 3890, 30, 76, 5.20, 2.40, 1500, "10-15 days"),
        ("Yoga Mat 6mm Non Slip with Strap", 26.99, 4.6, 11200, 19, 22, 6.90, 6.50, 4300, "12-20 days"),
    ],
    "outdoor": [
        ("Portable Camping Lantern Rechargeable Collapsible", 23.99, 4.6, 7310, 13, 57, 5.90, 2.80, 3800, "10-15 days"),
        ("Hammock Tree Straps Heavy Duty 2-Pack", 17.99, 4.8, 9920, 21, 48, 3.30, 1.90, 5100, "9-14 days"),
        ("Waterproof Dry Bag 20L Roll Top", 19.99, 4.6, 4150, 33, 61, 4.80, 2.60, 2600, "10-16 days"),
    ],
    "office": [
        ("Monitor Stand Riser with Drawer Bamboo", 34.99, 4.5, 3640, 16, 64, 11.20, 6.10, 900, "12-18 days"),
        ("Cable Management Box Large with Lid", 23.99, 4.5, 5580, 26, 71, 6.40, 3.80, 1900, "10-16 days"),
        ("Desk Mat Leather 31x15 Dual Sided", 16.99, 4.6, 8870, 8, 25, 3.10, 2.20, 7300, "9-14 days"),
    ],
    "baby": [
        ("Silicone Baby Bibs Waterproof Set of 3", 15.99, 4.7, 10300, 10, 42, 2.60, 1.40, 6600, "9-14 days"),
        ("Baby Nail Trimmer Electric Quiet", 24.99, 4.4, 4020, 23, 69, 6.10, 1.90, 2400, "10-15 days"),
        ("Stroller Organizer with Cup Holders", 21.99, 4.5, 6100, 35, 77, 5.40, 2.70, 1800, "10-16 days"),
    ],
}


def _seed(*parts) -> random.Random:
    h = hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()
    return random.Random(int(h[:12], 16))


def candidates(category: str) -> List[Listing]:
    out = []
    for i, (title, price, rating, reviews, rank, before, *_rest) in enumerate(CATALOG.get(category, [])):
        asin = "DEMO" + hashlib.sha1(title.encode()).hexdigest()[:6].upper()
        out.append(Listing(source="amazon", side=SELL, source_id=asin, title=title,
                           url=f"https://www.amazon.com/s?k={title.split(' ')[0]}", price=price,
                           rating=rating, review_count=reviews, rank=rank, rank_before=before,
                           has_prime=True, raw={"sponsored_on_page": 3 + i * 2, "demo": True}))
    return out


def suppliers(sell: Listing, category: str) -> List[Listing]:
    for row in CATALOG.get(category, []):
        if row[0] == sell.title:
            title, _, _, _, _, _, cost, ship, sold, days = row
            r = _seed(title)
            alt = round(cost * (1 + r.uniform(0.08, 0.25)), 2)
            return [
                Listing(source="aliexpress", side=SUPPLY, source_id="DEMO1" + sell.source_id[4:], title=title.lower(),
                        url="https://www.aliexpress.com", price=cost, shipping_cost=ship, sold_count=sold,
                        rating=round(r.uniform(4.5, 4.9), 1), shipping_days=days, raw={"demo": True}),
                Listing(source="aliexpress", side=SUPPLY, source_id="DEMO2" + sell.source_id[4:], title=title.lower(),
                        url="https://www.aliexpress.com", price=alt, shipping_cost=0.0, sold_count=sold // 3,
                        rating=round(r.uniform(4.2, 4.7), 1), shipping_days=days, raw={"demo": True}),
            ]
    return []


def search(query: str) -> List[tuple]:
    """(sell listing, category) pairs whose title shares a word with the query."""
    q = {w for w in query.lower().split() if len(w) > 2}
    hits = []
    for cat in CATALOG:
        for l in candidates(cat):
            if q & set(l.title.lower().split()):
                hits.append((l, cat))
    return hits[:8] or [(l, "kitchen") for l in candidates("kitchen")]


def drift(asin: str, base_sell: float, base_cost: float, day: date) -> tuple:
    """Deterministic daily wobble so the Watch job produces believable changes in demo mode."""
    r = _seed(asin, day.isoformat())
    return round(base_sell * (1 + r.uniform(-0.16, 0.12)), 2), round(base_cost * (1 + r.uniform(-0.05, 0.22)), 2)
