"""Small launch add-on: keywords, a listing title, and ad angles. Optional LLM polish."""
from __future__ import annotations

import json
import re
from typing import Dict

import httpx

from ..config import settings

FEATURE_WORDS = ["non-stick", "rechargeable", "waterproof", "collapsible", "stainless steel", "silicone", "adjustable",
                 "reflective", "leak proof", "cordless", "magnetic", "bamboo", "quiet", "heavy duty", "portable",
                 "suction", "dual sided", "no pull", "heatless", "motion sensor", "roll top"]


def keywords(title: str) -> list:
    t = re.sub(r"[^a-z\s-]", " ", title.lower())
    words = [w for w in t.split() if len(w) > 2 and w not in {"set", "pack", "with", "and", "for", "inch", "piece"}]
    bigrams = [f"{a} {b}" for a, b in zip(words, words[1:])]
    seen, out = set(), []
    for k in bigrams[:4] + words[:4]:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out[:6]


def build(title: str, profit: Dict) -> Dict:
    t = title.lower()
    feats = [f for f in FEATURE_WORDS if f in t][:3]
    angles = [f"Lead with {f}: show it in the first 2 seconds of the ad" for f in feats]
    if profit.get("sell"):
        angles.append(f"Price it as a gift under ${int(profit['sell']) + 1}")
    return {"keywords": keywords(title), "listing_title": title[:120], "angles": angles[:3], "source": "rules"}


async def polish(title: str, base: Dict) -> Dict:
    """Optional: rewrite angles with an LLM. Falls back silently to the rule-based version."""
    if not settings.openai_api_key:
        return base
    prompt = (f"Product: {title}\nWrite 3 short ad angles (max 14 words each) and one Amazon-style listing title "
              "(max 120 chars) for a dropshipper. Plain claims only, no invented specs. "
              'Return JSON: {"angles": [...], "listing_title": "..."}')
    try:
        async with httpx.AsyncClient(timeout=25) as c:
            r = await c.post("https://api.openai.com/v1/chat/completions",
                             headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                             json={"model": "gpt-4o-mini", "temperature": 0.4, "response_format": {"type": "json_object"},
                                   "messages": [{"role": "user", "content": prompt}]})
        if r.status_code == 200:
            j = json.loads(r.json()["choices"][0]["message"]["content"])
            return {**base, "angles": j.get("angles", base["angles"])[:3],
                    "listing_title": j.get("listing_title", base["listing_title"])[:120], "source": "ai"}
    except Exception:
        pass
    return base
