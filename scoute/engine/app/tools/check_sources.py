"""
Check live data sources from the terminal (run from the engine/ folder):

    python -m app.tools.check_sources amazon "silicone baking mat"
    python -m app.tools.check_sources movers kitchen
    python -m app.tools.check_sources aliexpress "silicone baking mat"
    python -m app.tools.check_sources full "silicone baking mat"     # Amazon -> AliExpress -> profit
    python -m app.tools.check_sources price B0XXXXXXXX              # 4-method price vote on a live product page
    python -m app.tools.check_sources price-file debug/amazon_product_last.html   # same, on a saved page (offline)

Pages that parse to nothing are saved in debug/ so selectors can be fixed.
"""
from __future__ import annotations

import asyncio
import sys

from ..engine.analyze import opportunity
from ..engine.tables import load
from ..extract import extract_price
from ..fetch import close_all
from ..sources import aliexpress, amazon, ebay


def show_vote(r):
    print(f"\n=== Price vote: {r.status.upper()}  price={r.price}  confidence={r.confidence}")
    print(f"    reason: {r.reason}")
    for m, v in r.methods.items():
        print(f"    {m:<11} {v if v is not None else '— (nothing found)'}")
    print("    usable:", r.usable, "(only verified/likely prices are ever shown to users)")


def load_file(path):
    import os
    if not os.path.isfile(path):
        raise SystemExit(f"File not found: {path}\nSaved pages are in the debug/ folder, e.g. debug/amazon_product_last.html")
    try:
        from scrapling.parser import Selector
    except ImportError:
        from scrapling.parser import Adaptor as Selector
    with open(path, encoding="utf-8", errors="ignore") as f:
        return Selector(f.read())


def show(rows, title):
    print(f"\n=== {title}: {len(rows)} results")
    for l in rows[:8]:
        extra = [x for x in (f"{l.rating}★" if l.rating else "", f"{l.review_count:,} reviews" if l.review_count else "",
                             f"{l.sold_count:,} sold" if l.sold_count else "",
                             f"rank {l.rank_before}→{l.rank}" if l.rank else "",
                             ("free ship" if l.shipping_cost == 0 else f"+${l.shipping_cost} ship") if l.shipping_cost is not None else "",
                             f"from {l.original_currency}" if l.original_currency != "USD" else "") if x]
        price = f"${l.price:.2f}" if l.price else "—"
        print(f"  {price:>9}  {l.title[:62]:<62} {' · '.join(extra)}")


async def main(kind: str, arg: str):
    if kind == "amazon":
        show(await amazon.search(arg, 10), "Amazon search")
    elif kind == "movers":
        show(await amazon.movers(load("categories")[arg]["movers"]), f"Movers & Shakers ({arg})")
    elif kind == "aliexpress":
        show(await aliexpress.search(arg, 8), "AliExpress")
    elif kind == "ebay":
        print("eBay keys set:", ebay.enabled())
        show(await ebay.search(arg, 8), "eBay")
    elif kind == "full":
        sells = await amazon.search(arg, 3)
        show(sells, "Amazon")
        for s in sells[:3]:
            q = aliexpress.cost_query(s.title)
            sups = await aliexpress.search(q, 6)
            show(sups, f"AliExpress for '{q}'")
            o = await opportunity(s, sups, "default", {})
            p = o.get("profit") or {}
            print(f"  → {o['action']}  net ${p.get('net', 0):.2f}  max buy ${p.get('max_buy_price', 0):.2f}  "
                  f"match {o['match_confidence']}  safety {(o.get('failure') or {}).get('safety')}")
    elif kind == "price":
        show_vote(await amazon.current_price(arg.strip()))
    elif kind == "price-file":
        site = "aliexpress" if "aliexpress" in arg.lower() else "amazon"
        show_vote(await extract_price(load_file(arg.strip()), site, "product"))
    else:
        print(__doc__)


async def _run(kind: str, arg: str):
    try:
        await main(kind, arg)
    finally:
        await close_all()      # close the browser before Python exits


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
    else:
        asyncio.run(_run(sys.argv[1], " ".join(sys.argv[2:])))