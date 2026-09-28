"""
Business workflows: build a category feed, run a search job, recalc the watchlist.
All run in the background worker thread (see jobs.py), never inside a web request.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime
from typing import Dict, List, Optional

from sqlalchemy import delete, select

from .config import settings
from .db import SessionLocal
from .engine import analyze as A
from .engine.tables import load
from .listing import Listing
from .models import Alert, FeedRun, Opportunity, SearchJob, User, WatchItem, Workspace
from .notify import send_alert_email
from .sources import aliexpress, amazon, demo, ebay
from .sources import risk as risk_gate

SUPPLIER_LOOKUPS_PER_CATEGORY = 25


def _row(o: Dict, origin: str, feed_day: date) -> Opportunity:
    p = o.get("profit") or {}
    f = o.get("failure") or {}
    return Opportunity(origin=origin, category=o["category"], feed_date=feed_day, mode=o["mode"],
                       asin=o["sell"]["source_id"], title=o["sell"]["title"][:500],
                       image_url=(o["sell"].get("image_url") or "")[:800], action=o["action"],
                       net_profit=p.get("net", 0.0), margin=p.get("margin", 0.0), sell_price=o["sell"].get("price") or 0.0,
                       safety=f.get("safety", "LOW"), rank_score=A.rank_score(o), is_demo=o["is_demo"], data=o)


async def _suppliers_for(sell: Listing, category: str, mode: str) -> List[Listing]:
    if settings.demo:
        return demo.suppliers(sell, category)
    from .engine.entity import extract_entity
    entity = extract_entity(sell.title)
    q = aliexpress.cost_query(sell.title)
    try:
        if mode == "resell":
            return await ebay.search(q, 6) if ebay.enabled() else []
        results = await aliexpress.search(q, 6)
        if not results and entity.canonical_query and entity.canonical_query != q:
            results = await aliexpress.search(entity.canonical_query, 6)
        return results
    except Exception as e:
        print(f"[supplier] {e.__class__.__name__}: {e}")
        return []


# ---------------------------------------------------------------- FEED
async def build_feed(category: str) -> Dict:
    today = date.today()
    db = SessionLocal()
    run = FeedRun(category=category, feed_date=today)
    db.add(run)
    db.commit()
    notes: Dict = {}
    try:
        if settings.demo:
            cands = demo.candidates(category)
            notes["source"] = "demo"
        else:
            slug = load("categories")[category]["movers"]
            cands: List[Listing] = []
            try:
                cands = await amazon.movers(slug, 60)
                notes["movers"] = len(cands)
            except Exception as e:
                notes["movers_error"] = f"{e.__class__.__name__}: {e}"
            if len(cands) < 10:
                try:
                    extra = await amazon.search(load("categories")[category]["search"], 20)
                    cands += [c for c in extra if all(c.source_id != x.source_id for x in cands)]
                    notes["search"] = len(extra)
                except Exception as e:
                    notes["search_error"] = f"{e.__class__.__name__}: {e}"
        run.candidates = len(cands)

        # cheap pre-filter before any supplier lookup
        pre = [c for c in cands if c.price and 8 <= c.price <= 150 and (c.rating or 4.0) >= 3.8
               and "dropship" in risk_gate.evaluate(c.title, c.brand)["modes"]]
        pre.sort(key=lambda c: (c.rank or 999))
        opps = []
        for sell in pre[:SUPPLIER_LOOKUPS_PER_CATEGORY]:
            sups = await _suppliers_for(sell, category, "dropship")
            o = await A.opportunity(sell, sups, category, {}, "dropship", "US", "china", "shopify", demo=settings.demo)
            if o["action"] in ("SOURCE", "SOURCE_SMALL", "WAIT"):
                opps.append(o)

        db.execute(delete(Opportunity).where(Opportunity.origin == "feed", Opportunity.category == category,
                                             Opportunity.feed_date == today))
        for o in sorted(opps, key=A.rank_score, reverse=True)[:20]:
            db.add(_row(o, "feed", today))
        run.published = min(len(opps), 20)
        run.status = "done"
    except Exception as e:
        run.status = "failed"
        notes["error"] = f"{e.__class__.__name__}: {e}"
        print(f"[feed] {category} failed: {e}")
    run.notes = notes
    run.finished_at = datetime.utcnow()
    db.commit()
    db.close()
    print(f"[feed] {category}: {run.candidates} candidates → {run.published} published ({run.status})")
    return {"category": category, "status": run.status, "published": run.published, "notes": notes}


async def build_all_feeds() -> List[Dict]:
    return [await build_feed(c) for c in settings.feed_categories]


# ---------------------------------------------------------------- SEARCH
async def run_search(job_id: str):
    db = SessionLocal()
    job = db.get(SearchJob, job_id)
    user = db.get(User, job.user_id)
    ws = db.execute(select(Workspace).where(Workspace.owner_id == user.id, Workspace.is_default == True)).scalar_one_or_none()  # noqa: E712
    brief = (ws.brief if ws else {}) or {}
    job.status, job.progress = "running", "Searching marketplaces"
    db.commit()
    try:
        if settings.demo:
            pairs = demo.search(job.query)
            job.sources = {"amazon": "demo", "aliexpress": "demo"}
        else:
            found = await amazon.search(job.query, 8)
            pairs = [(l, "search") for l in found]
            job.sources = {"amazon": f"ok ({len(found)})"}
        ids = []
        for n, (sell, cat) in enumerate(pairs[:6], 1):
            job.progress = f"Checking supplier costs {n}/{min(len(pairs), 6)}"
            db.commit()
            sups = await _suppliers_for(sell, cat, job.mode)
            o = await A.opportunity(sell, sups, cat if cat != "search" else "default", user.settings or {},
                                    job.mode, brief.get("market", "US"), brief.get("sourcing", "china"),
                                    brief.get("channel", "shopify"), demo=settings.demo)
            row = _row(o, "search", date.today())
            db.add(row)
            db.flush()
            ids.append(row.id)
        job.result_ids = ids
        job.status, job.progress = "done", f"{len(ids)} products analysed"
    except Exception as e:
        job.status, job.error = "failed", f"{e.__class__.__name__}: {e}"
        job.progress = "Search failed"
    db.commit()
    db.close()


# ---------------------------------------------------------------- WATCH
def _alert_kind(old: Dict, new: Dict) -> Optional[str]:
    o, n = old.get("net", 0), new.get("net", 0)
    if o > 0 and n <= 0:
        return "destroyed"
    if o > 0 and n < o * 0.75:
        return "weakened"
    if n > 0 and o >= 0 and n > max(o, 0.01) * 1.25:
        return "improved"
    if old.get("action") in ("SOURCE", "SOURCE_SMALL") and new.get("action") == "SKIP":
        return "destroyed"
    return None


async def recalc_watch() -> int:
    db = SessionLocal()
    items = db.execute(select(WatchItem)).scalars().all()
    made = 0
    for w in items:
        inputs = dict(w.inputs)
        sell0, sup0 = inputs["sell"], inputs["supplier"]
        try:
            if settings.demo or w.asin.startswith("DEMO"):
                inputs["sell"], inputs["supplier"] = demo.drift(w.asin, w.inputs.get("sell_base", sell0),
                                                                w.inputs.get("supplier_base", sup0), date.today())
            else:
                pr = await amazon.current_price(w.asin, w.title)
                if pr.usable:
                    inputs["sell"] = pr.price
                else:
                    print(f"[watch] {w.asin}: price {pr.status} ({pr.reason}) — keeping last known price")
                sup_url = w.inputs.get("supplier_url")
                if sup_url and "aliexpress" in sup_url:
                    sp = await aliexpress.item_price(sup_url)
                    if sp:
                        inputs["supplier"] = sp
        except Exception as e:
            print(f"[watch] {w.title[:40]}: {e.__class__.__name__}")
        calc_in = {k: v for k, v in inputs.items() if k not in ("sell_base", "supplier_base", "supplier_url")}
        res = A.evaluate(calc_in, 0.8, 0.8, None, None, False)
        new = {"net": res["profit"]["net"], "margin": res["profit"]["margin"], "action": res["verdict"]["action"],
               "safety": res["failure"]["safety"], "sell": inputs["sell"], "supplier": inputs["supplier"],
               "max_buy_price": res["profit"]["max_buy_price"]}
        kind = _alert_kind(w.last_result or {}, new)
        if kind:
            old = w.last_result or {}
            title = {"destroyed": "Opportunity destroyed", "weakened": "Opportunity weakened",
                     "improved": "Opportunity improved"}[kind] + f": {w.title[:60]}"
            body = (f"Profit per sale ${old.get('net', 0):.2f} → ${new['net']:.2f}. "
                    f"Selling price ${old.get('sell', 0):.2f} → ${new['sell']:.2f}, "
                    f"supplier ${old.get('supplier', 0):.2f} → ${new['supplier']:.2f}. "
                    f"Now: {new['action'].replace('_', ' ').title()}.")
            db.add(Alert(workspace_id=w.workspace_id, watch_id=w.id, kind=kind, title=title, body=body))
            ws = db.get(Workspace, w.workspace_id)
            owner = db.get(User, ws.owner_id) if ws else None
            if owner and (owner.settings or {}).get("alert_email", True):
                await send_alert_email(owner.email, title, body)
            made += 1
        w.inputs = {**w.inputs, "sell": inputs["sell"], "supplier": inputs["supplier"]}
        w.last_result = new
        w.history = (w.history or [])[-59:] + [{"date": date.today().isoformat(), "net": new["net"], "action": new["action"]}]
        w.last_checked = datetime.utcnow()
    db.commit()
    db.close()
    print(f"[watch] {len(items)} items checked, {made} alerts")
    return made
