"""
Save any page exactly as Scoute's browser sees it, for fixing selectors.

    python -m app.tools.save_page aliexpress "silicone baking mat"
    python -m app.tools.save_page url "https://www.amazon.com/dp/B073XRGZ7K"

Pages go to debug/<name>.html
"""
from __future__ import annotations

import asyncio
import os
import re
import sys

from ..fetch import browser_get, close_all, page_html


async def main(kind: str, arg: str):
    if kind == "aliexpress":
        slug = re.sub(r"-+", "-", re.sub(r"[^a-z0-9-]", "", arg.lower().replace(" ", "-"))).strip("-")
        url = f"https://www.aliexpress.com/w/wholesale-{slug}.html?g=y&SearchText={slug.replace('-', '+')}"
        profile, name = "dynamic", "aliexpress_search"
    elif kind == "url":
        url = arg.strip()
        profile = "dynamic" if "aliexpress" in url else "light"
        name = "aliexpress_page" if "aliexpress" in url else "amazon_page"
    else:
        print(__doc__)
        return
    try:
        page = await browser_get(url, profile)
        os.makedirs("debug", exist_ok=True)
        path = os.path.join("debug", f"{name}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(page_html(page))
        print(f"Saved {path} ({os.path.getsize(path):,} bytes)")
    finally:
        await close_all()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
    else:
        asyncio.run(main(sys.argv[1], " ".join(sys.argv[2:])))