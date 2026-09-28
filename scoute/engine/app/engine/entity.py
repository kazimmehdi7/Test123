"""
Structured Product Entity & Spec Extractor.
Extracts canonical product nouns, materials, dimensions/specifications, pack quantities,
and product noun clusters from noisy e-commerce marketplace titles.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

# Common materials in e-commerce products
MATERIALS: Set[str] = {
    "silicone", "stainless steel", "stainless", "bamboo", "wooden", "wood", "ceramic",
    "glass", "cast iron", "aluminum", "aluminium", "plastic", "leather", "cotton",
    "linen", "microfiber", "nylon", "polyester", "silk", "wool", "canvas", "titanium",
    "carbon fiber", "rubber", "latex", "acrylic", "brass", "copper", "porcelain", "zinc",
    "memory foam", "velvet", "fleece", "mesh", "neoprene", "stone", "marble", "granite"
}

# Marketing buzzwords & noise tokens to remove from search query creation
NOISE_WORDS: Set[str] = {
    "upgraded", "upgrade", "newest", "2024", "2025", "2026", "2027", "hot", "best", "top",
    "premium", "luxury", "high quality", "quality", "pro", "professional", "great", "perfect",
    "super", "ultra", "extra", "multi-functional", "multifunctional", "durable", "heavy duty",
    "portable", "collapsible", "foldable", "reusable", "disposable", "universal", "adjustable",
    "ergonomic", "modern", "fashion", "stylish", "creative", "cute", "essential", "must have",
    "non-stick", "nonstick", "heat resistant", "heat-resistant", "easy clean", "food grade"
}

# Synonymous Product Noun Clusters (Cluster ID -> Set of equivalent terms)
NOUN_CLUSTERS: Dict[str, Set[str]] = {
    "mat": {"mat", "mats", "pad", "pads", "sheet", "sheets", "liner", "liners", "sling", "slings"},
    "utensil_spatula": {"spatula", "spatulas", "scraper", "scrapers", "turner", "turners", "flipper"},
    "utensil_spoon": {"spoon", "spoons", "ladle", "ladles", "scoop", "scoops"},
    "utensil_tongs": {"tong", "tongs", "pincer", "clamp"},
    "utensil_whisk": {"whisk", "whisks", "beater", "mixer"},
    "cutter_knife": {"knife", "knives", "cutter", "cutters", "slicer", "slicers", "chopper", "choppers", "blade", "blades"},
    "drinkware": {"bottle", "bottles", "tumbler", "tumblers", "cup", "cups", "flask", "flasks", "mug", "mugs", "jug", "thermos"},
    "board": {"board", "boards", "platter", "block"},
    "container": {"container", "containers", "box", "boxes", "jar", "jars", "bin", "bins", "organizer", "organizers"},
    "pet_wear": {"harness", "harnesses", "vest", "vests", "collar", "collars", "leash", "leashes"},
    "lighting": {"lamp", "lamps", "light", "lights", "lantern", "lanterns", "bulb", "bulbs", "strip"},
    "cleaning": {"brush", "brushes", "sponge", "sponges", "cloth", "cloths", "mop", "mops", "duster", "towel", "towels"},
    "bag": {"bag", "bags", "pouch", "pouches", "backpack", "backpacks", "tote", "totes", "case", "cases"},
    # fitness — previously uncovered, so cluster-based mismatch protection silently did
    # nothing for this whole feed category (see matching.py's head-noun fallback for the
    # general case; curated entries here are still better where they exist).
    "fitness_band": {"band", "bands", "resistance"},
    "fitness_rope": {"rope", "ropes", "jumprope"},
    "fitness_weight": {"dumbbell", "dumbbells", "kettlebell", "kettlebells", "weight", "weights"},
    # yoga/desk mats fall under the existing "mat" cluster above — no separate entry needed.
    # office — previously uncovered
    "desk_riser": {"riser", "stand", "monitor"},
    "cable": {"cable", "cables", "cord", "cords"},
    # baby — previously uncovered
    "baby_bib": {"bib", "bibs"},
    "baby_trimmer": {"trimmer", "clipper", "clippers"},
    "stroller": {"stroller", "strollers", "pram"},
}

# Regexes for extracting pack quantity
PACK_REGEXES: List[re.Pattern] = [
    # "N/Mpcs" (e.g. "1/2PCS" — an AliExpress variant selector, "buy 1 or 2") must be checked
    # before the generic "(\d+)\s*pcs" pattern below: that pattern's word boundary happily
    # matches the "2pcs" tail of "1/2pcs" on its own, silently returning 2 instead of the 1
    # the whole "N/M" pattern actually means. Order here matters — most specific first.
    re.compile(r"\b(\d{1,3})\s*/\s*\d{1,3}\s*pcs\b", re.I),
    re.compile(r"\b(?:set|pack|box|lot)\s+of\s+(\d{1,3})\b", re.I),
    re.compile(r"\b(\d{1,3})\s*[-\s]?\s*(?:pack|pk|pcs|pc|pieces|piece|count|ct|packs|sheets|mats|pairs|prs)\b", re.I),
    re.compile(r"\b(\d{1,3})\s*[-\s]?\s*in\s*[-\s]?\s*1\b", re.I),  # "3-in-1" or "3 in 1"
]

# Regexes for extracting dimensions / measurements
DIMENSION_REGEXES: List[re.Pattern] = [
    # 28x20 in, 60x40 cm, 16"x24"
    re.compile(r"(\d+(?:\.\d+)?\s*(?:x|\*|by)\s*\d+(?:\.\d+)?(?:\s*(?:x|\*|by)\s*\d+(?:\.\d+)?)?\s*(?:in|inch|inches|\"|cm|mm|ft|m)\b)", re.I),
    # 12 inch, 30cm, 500ml, 32oz, 2L, 5qt
    re.compile(r"(\b\d+(?:\.\d+)?\s*(?:inch|inches|\"|cm|mm|oz|fl\s*oz|ml|l|liter|liters|qt|quart|gallon|lbs|kg|g)\b)", re.I),
]


@dataclass
class ProductEntity:
    original_title: str
    canonical_query: str
    core_nouns: List[str]
    noun_cluster: Optional[str]
    material: Optional[str]
    pack_qty: int
    dimensions: List[str] = field(default_factory=list)
    brand_detected: Optional[str] = None
    specs: Dict[str, str] = field(default_factory=dict)


def extract_pack_qty(title: str) -> int:
    """Extract integer pack size (e.g. '3 Pack' -> 3, 'Set of 2' -> 2). Defaults to 1."""
    t = (title or "").strip()
    for rx in PACK_REGEXES:
        m = rx.search(t)
        if m:
            val = int(m.group(1))
            if 1 <= val <= 500:
                return val
    return 1


def extract_material(title: str) -> Optional[str]:
    """Find the primary material mentioned in the product title."""
    t = (title or "").lower()
    for mat in sorted(MATERIALS, key=lambda x: -len(x)):
        if re.search(rf"\b{re.escape(mat)}\b", t):
            return mat
    return None


def extract_noun_cluster(title: str) -> Optional[str]:
    """Identify the core functional product cluster (e.g. 'mat' vs 'spatula' vs 'knife')."""
    words = set(re.findall(r"[a-z0-9]+", (title or "").lower()))
    for cluster_id, cluster_words in NOUN_CLUSTERS.items():
        if words & cluster_words:
            return cluster_id
    return None


def extract_dimensions(title: str) -> List[str]:
    """Find dimensions, size measurements, or volume specs."""
    t = (title or "")
    dims: List[str] = []
    for rx in DIMENSION_REGEXES:
        for m in rx.finditer(t):
            dim_str = m.group(1).strip()
            if dim_str and dim_str not in dims:
                dims.append(dim_str)
    return dims


def extract_entity(title: str, brand: Optional[str] = None) -> ProductEntity:
    """
    Parse a noisy listing title into a canonical ProductEntity for accurate search and matching.
    """
    from ..sources.risk import MAJOR_BRANDS
    t_clean = (title or "").strip()
    low = t_clean.lower()

    # 1. Detect Brand
    detected_brand = None
    if brand:
        detected_brand = brand
    else:
        for b in sorted(MAJOR_BRANDS, key=len, reverse=True):
            if re.search(rf"\b{re.escape(b)}\b", low):
                detected_brand = b
                break

    # 2. Extract Pack Quantity & Material & Noun Cluster & Specs
    qty = extract_pack_qty(t_clean)
    material = extract_material(t_clean)
    cluster = extract_noun_cluster(t_clean)
    dims = extract_dimensions(t_clean)

    # 3. Clean string to build canonical core search query
    work = t_clean
    # Remove leading bracket tags like [2026 Upgraded], (Hot Deal)
    work = re.sub(r"^[\[\(][^\]\)]+[\]\)]\s*", "", work)

    # If very long title with pipe, dash or comma separators, take primary descriptor
    segments = re.split(r"\s*[,|–—]\s*|\s+-\s+", work)
    first_segment = segments[0].strip() if segments else work

    # Remove brands
    query_text = first_segment
    if detected_brand:
        query_text = re.sub(rf"(?i)\b{re.escape(detected_brand)}\b", " ", query_text)
    
    # House brands
    for hb in ("amazon basics", "amazonbasics", "amazon essentials", "basics"):
        query_text = re.sub(rf"(?i)\b{re.escape(hb)}\b", " ", query_text)

    # Remove noise words
    for nw in NOISE_WORDS:
        query_text = re.sub(rf"(?i)\b{re.escape(nw)}\b", " ", query_text)

    # Remove pack phrases and dimension strings from search query
    query_text = re.sub(r"(?i)\b(set of|pack of|lot of)\s*\d+\b|\b\d+\s*-?\s*(pack|pk|pcs|pieces|count)\b", " ", query_text)
    for d in dims:
        query_text = query_text.replace(d, " ")

    # Clean non-alphanumeric
    words = [
        w for w in re.sub(r"[^a-zA-Z0-9\s-]", " ", query_text).split()
        if len(w) > 2 and w.lower() not in {"the", "and", "for", "with", "set", "pack", "pcs"}
    ]

    core_nouns = words[:5]
    canonical = " ".join(core_nouns).lower()

    if qty > 1:
        canonical = f"{canonical} {qty}pcs"

    return ProductEntity(
        original_title=title,
        canonical_query=canonical.strip(),
        core_nouns=core_nouns,
        noun_cluster=cluster,
        material=material,
        pack_qty=qty,
        dimensions=dims,
        brand_detected=detected_brand,
        specs={"dimensions": dims[0]} if dims else {},
    )
