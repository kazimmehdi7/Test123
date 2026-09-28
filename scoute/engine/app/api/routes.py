from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from .. import jobs
from ..auth import check_pw, current_user, hash_pw, plan, token_for, use_search, workspace_for
from ..config import PLANS, settings
from ..db import get_db
from ..engine import analyze as A
from ..engine.sentinel import calculate_saturation_index, analyze_sentinel_health
from ..engine.tables import load
from ..models import Alert, FeedRun, Opportunity, SearchJob, SentinelProduct, User, WatchItem, Workspace
from .schemas import Brief, CheckoutIn, Login, RecalcIn, Register, SearchIn, SentinelIn, SettingsIn, WatchIn, WorkspaceIn

router = APIRouter(prefix="/api")

DEFAULT_BRIEF = Brief(categories=["kitchen", "pet", "home"]).model_dump()


def _user_out(u: User, db: Session) -> dict:
    ws = db.execute(select(Workspace).where(Workspace.owner_id == u.id).order_by(Workspace.created_at)).scalars().all()
    return {"id": u.id, "email": u.email, "name": u.name, "plan": u.plan, "limits": plan(u), "settings": u.settings,
            "workspaces": [_ws_out(w) for w in ws], "demo": settings.demo,
            "billing_enabled": bool(settings.stripe_secret_key)}


def _ws_out(w: Workspace) -> dict:
    return {"id": w.id, "name": w.name, "client_name": w.client_name, "logo_url": w.logo_url,
            "is_default": w.is_default, "brief": w.brief or {}, "has_brief": bool(w.brief)}


# ============================================================ meta
@router.get("/health")
def health():
    return {"ok": True, "demo": settings.demo, "jobs": jobs.status()}


@router.get("/meta")
def meta():
    cats = load("categories")
    return {"categories": [{"id": k, "label": v["label"]} for k, v in cats.items() if k in settings.feed_categories],
            "plans": PLANS, "channels": {k: v["label"] for k, v in load("channel_fees").items() if not k.startswith("_")},
            "demo": settings.demo, "duty_as_of": load("duty_rates").get("_as_of")}


# ============================================================ auth
@router.post("/auth/register")
def register(body: Register, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if "@" not in email:
        raise HTTPException(400, "Enter a valid email address")
    if db.execute(select(User).where(User.email == email)).scalar_one_or_none():
        raise HTTPException(409, "An account with this email already exists. Log in instead.")
    u = User(email=email, name=body.name.strip(), password_hash=hash_pw(body.password))
    db.add(u)
    db.flush()
    db.add(Workspace(owner_id=u.id, name="My workspace", is_default=True, brief={}))
    db.commit()
    return {"token": token_for(u), "user": _user_out(u, db)}


@router.post("/auth/login")
def login(body: Login, db: Session = Depends(get_db)):
    u = db.execute(select(User).where(User.email == body.email.strip().lower())).scalar_one_or_none()
    if not u or not check_pw(body.password, u.password_hash):
        raise HTTPException(401, "Email or password is incorrect")
    return {"token": token_for(u), "user": _user_out(u, db)}


@router.get("/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _user_out(user, db)


@router.patch("/me/settings")
def update_settings(body: SettingsIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    data = body.model_dump(exclude_none=True)
    if "name" in data:
        user.name = data.pop("name")
    user.settings = {**(user.settings or {}), **data}
    db.commit()
    return _user_out(user, db)


# ============================================================ workspaces + brief
@router.get("/workspaces")
def list_workspaces(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _user_out(user, db)["workspaces"]


@router.post("/workspaces")
def create_workspace(body: WorkspaceIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    count = db.execute(select(func.count()).select_from(Workspace).where(Workspace.owner_id == user.id)).scalar()
    if count >= plan(user)["workspaces"]:
        raise HTTPException(403, "Client workspaces are part of the Business plan.")
    w = Workspace(owner_id=user.id, name=body.name, client_name=body.client_name, logo_url=body.logo_url, brief={})
    db.add(w)
    db.commit()
    return _ws_out(w)


@router.patch("/workspaces/{wid}")
def edit_workspace(wid: str, body: WorkspaceIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    w = workspace_for(user, wid, db)
    w.name, w.client_name, w.logo_url = body.name, body.client_name, body.logo_url
    db.commit()
    return _ws_out(w)


@router.delete("/workspaces/{wid}")
def delete_workspace(wid: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    w = workspace_for(user, wid, db)
    if w.is_default:
        raise HTTPException(400, "Your main workspace can't be deleted")
    db.delete(w)
    db.commit()
    return {"ok": True}


@router.put("/workspaces/{wid}/brief")
def save_brief(wid: str, body: Brief, user: User = Depends(current_user), db: Session = Depends(get_db)):
    w = workspace_for(user, wid, db)
    allowed = set(settings.feed_categories)
    cats = [c for c in body.categories if c in allowed][: (3 if user.plan == "free" else 8)]
    w.brief = {**body.model_dump(), "categories": cats or ["kitchen"]}
    db.commit()
    return _ws_out(w)


# ============================================================ feed
def _card(o: Opportunity, full: bool) -> dict:
    d = o.data or {}
    p, f = d.get("profit") or {}, d.get("failure") or {}
    card = {"id": o.id, "title": o.title, "category": o.category, "image_url": o.image_url, "action": o.action,
            "net": o.net_profit if p else None, "margin": o.margin if p else None,
            "sell": o.sell_price or None, "safety": o.safety if f else None,
            "why_today": d.get("why_today"), "is_demo": o.is_demo, "feed_date": o.feed_date.isoformat(),
            "supplier_price": (d.get("supplier") or {}).get("price"), "supplier_ship": (d.get("supplier") or {}).get("shipping_cost"),
            "duty": p.get("duty"), "costs": round((p.get("fees", 0) + p.get("ads", 0) + p.get("returns", 0) + p.get("buffer", 0)), 2),
            "locked": not full}
    if full:
        card.update(max_buy_price=p.get("max_buy_price"), max_ad_per_sale=p.get("max_ad_per_sale"),
                    break_sell=next((x["break_point"] for x in f.get("points", []) if x["key"] == "sell"), None),
                    break_supplier=next((x["break_point"] for x in f.get("points", []) if x["key"] == "supplier"), None))
    return card


@router.get("/feed")
def feed(workspace_id: Optional[str] = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ws = workspace_for(user, workspace_id, db)
    brief = ws.brief or DEFAULT_BRIEF
    latest = db.execute(select(func.max(Opportunity.feed_date)).where(Opportunity.origin == "feed")).scalar()
    if not latest:
        return {"items": [], "date": None, "brief": brief, "building": jobs.status()["running"]["batch"], "total": 0}
    q = (select(Opportunity).where(Opportunity.origin == "feed", Opportunity.feed_date == latest,
                                   Opportunity.category.in_(brief.get("categories") or ["kitchen"]),
                                   Opportunity.sell_price >= brief.get("price_min", 0),
                                   Opportunity.sell_price <= brief.get("price_max", 9999))
         .order_by(desc(Opportunity.rank_score)))
    rows = [r for r in db.execute(q).scalars().all()
            if r.action == "WAIT" or (r.margin >= brief.get("min_margin", 0) and r.net_profit >= brief.get("min_profit", 0))]
    limit = plan(user)["feed_items"]
    items = [_card(r, full=(user.plan != "free" or i < limit)) for i, r in enumerate(rows)]
    return {"items": items, "date": latest.isoformat(), "brief": brief, "total": len(rows), "free_limit": limit,
            "building": jobs.status()["running"]["batch"]}


# ============================================================ opportunity detail
def _detail(o: Opportunity, user: User, rank_in_feed: Optional[int] = None) -> dict:
    d = dict(o.data or {})
    full = plan(user)["full_detail"] or (rank_in_feed is not None and rank_in_feed < plan(user)["feed_items"])
    if not full and d.get("profit"):
        d["failure"] = None
        d["profit"] = {k: d["profit"][k] for k in ("net", "margin", "sell", "target")}
        d["profit_alt"] = None
        d["launch"] = None
    return {"id": o.id, "origin": o.origin, "locked": not full, **d}


@router.get("/opportunities/{oid}")
def get_opportunity(oid: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    o = db.get(Opportunity, oid)
    if not o:
        raise HTTPException(404, "This opportunity is no longer available")
    idx = None
    if o.origin == "feed" and user.plan == "free":
        ids = db.execute(select(Opportunity.id).where(Opportunity.origin == "feed", Opportunity.feed_date == o.feed_date)
                         .order_by(desc(Opportunity.rank_score))).scalars().all()
        idx = ids.index(o.id) if o.id in ids else None
    elif o.origin == "search":
        idx = 0
    return _detail(o, user, idx)


@router.post("/opportunities/{oid}/recalc")
def recalc(oid: str, body: RecalcIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Recalculate with the user's own numbers (their supplier price, ad cost, duty rate…)."""
    if not plan(user)["full_detail"]:
        raise HTTPException(403, "Editing the numbers is part of the Pro plan.")
    o = db.get(Opportunity, oid)
    if not o:
        raise HTTPException(404, "Not found")
    d = o.data
    s = d["sell"]
    base = d.get("inputs")
    if not base:
        if "supplier" not in body.overrides:
            raise HTTPException(400, "Enter your supplier's price to calculate profit")
        built = A.build_inputs(s.get("price") or float(body.overrides.get("sell", 0)), float(body.overrides["supplier"]),
                               float(body.overrides.get("ship", 4.0)), d["category"], s["title"], user.settings,
                               d.get("channel", "shopify"), d.get("market", "US"), d.get("sourcing", "china"), d.get("mode", "dropship"))
        base = built["inputs"]
    inputs = {**base, **{k: (v if k == "channel" else float(v)) for k, v in body.overrides.items() if k in base and v not in (None, "")}}
    res = A.evaluate(inputs, max(d.get("confidence", 0.6), 0.7), max(d.get("match_confidence", 0.6), 0.75),
                     s.get("rank"), s.get("rank_before"), d["risk"]["modes"] == ["affiliate"] and d.get("mode") != "affiliate")
    return {"inputs": inputs, **res}


# ============================================================ search
@router.post("/search")
def start_search(body: SearchIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    remaining = use_search(user, db)
    job = SearchJob(user_id=user.id, query=body.query.strip(), mode=body.mode)
    db.add(job)
    db.commit()
    jobs.submit("search", job.id)
    return {"job_id": job.id, "remaining_today": remaining}


@router.get("/search/{job_id}")
def search_status(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    job = db.get(SearchJob, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(404, "Search not found")
    items = []
    if job.status == "done":
        rows = [db.get(Opportunity, i) for i in job.result_ids]
        items = [_card(r, plan(user)["full_detail"]) for r in rows if r]
        items.sort(key=lambda c: ({"SOURCE": 0, "SOURCE_SMALL": 1, "WAIT": 2, "NO_MATCH": 3, "SKIP": 4}.get(c["action"], 5), -(c["net"] or 0)))
    return {"status": job.status, "progress": job.progress, "error": job.error, "query": job.query, "items": items}


@router.get("/searches")
def recent_searches(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(SearchJob).where(SearchJob.user_id == user.id).order_by(desc(SearchJob.created_at)).limit(10)).scalars().all()
    return [{"id": r.id, "query": r.query, "status": r.status, "created_at": r.created_at.isoformat()} for r in rows]


# ============================================================ watchlist + alerts
@router.get("/watchlist")
def watchlist(workspace_id: Optional[str] = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ws = workspace_for(user, workspace_id, db)
    rows = db.execute(select(WatchItem).where(WatchItem.workspace_id == ws.id).order_by(desc(WatchItem.created_at))).scalars().all()
    return [{"id": w.id, "opportunity_id": w.opportunity_id, "title": w.title, "last": w.last_result, "history": w.history,
             "last_checked": w.last_checked.isoformat() if w.last_checked else None} for w in rows]


@router.post("/watchlist")
def add_watch(body: WatchIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    limit = plan(user)["watch_items"]
    if limit == 0:
        raise HTTPException(403, "Watching opportunities is part of the Pro plan.")
    ws = workspace_for(user, body.workspace_id, db)
    count = db.execute(select(func.count()).select_from(WatchItem).where(WatchItem.workspace_id == ws.id)).scalar()
    if count >= limit:
        raise HTTPException(403, f"Your plan watches up to {limit} products. Remove one to add another.")
    o = db.get(Opportunity, body.opportunity_id)
    if not o or not o.data.get("inputs"):
        raise HTTPException(400, "Only products with a calculated profit can be watched")
    exists = db.execute(select(WatchItem).where(WatchItem.workspace_id == ws.id, WatchItem.opportunity_id == o.id)).scalar_one_or_none()
    if exists:
        return {"id": exists.id, "already": True}
    inputs = {**o.data["inputs"], **{k: float(v) for k, v in body.overrides.items() if k in o.data["inputs"] and k != "channel"}}
    res = A.evaluate(inputs, 0.8, 0.8, None, None, False)
    w = WatchItem(workspace_id=ws.id, opportunity_id=o.id, title=o.title, asin=o.asin,
                  inputs={**inputs, "sell_base": inputs["sell"], "supplier_base": inputs["supplier"],
                          "supplier_url": (o.data.get("supplier") or {}).get("url")},
                  last_result={"net": res["profit"]["net"], "margin": res["profit"]["margin"], "action": res["verdict"]["action"],
                               "safety": res["failure"]["safety"], "sell": inputs["sell"], "supplier": inputs["supplier"],
                               "max_buy_price": res["profit"]["max_buy_price"]},
                  history=[{"date": date.today().isoformat(), "net": res["profit"]["net"], "action": res["verdict"]["action"]}],
                  last_checked=datetime.utcnow())
    db.add(w)
    db.commit()
    return {"id": w.id}


@router.delete("/watchlist/{wid}")
def remove_watch(wid: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    w = db.get(WatchItem, wid)
    if not w:
        raise HTTPException(404, "Not found")
    workspace_for(user, w.workspace_id, db)
    db.delete(w)
    db.commit()
    return {"ok": True}


@router.get("/alerts")
def alerts(workspace_id: Optional[str] = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ws = workspace_for(user, workspace_id, db)
    rows = db.execute(select(Alert).where(Alert.workspace_id == ws.id).order_by(desc(Alert.created_at)).limit(50)).scalars().all()
    return [{"id": a.id, "kind": a.kind, "title": a.title, "body": a.body, "read": a.read, "watch_id": a.watch_id,
             "created_at": a.created_at.isoformat()} for a in rows]


@router.post("/alerts/read")
def read_alerts(workspace_id: Optional[str] = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ws = workspace_for(user, workspace_id, db)
    for a in db.execute(select(Alert).where(Alert.workspace_id == ws.id, Alert.read == False)).scalars():  # noqa: E712
        a.read = True
    db.commit()
    return {"ok": True}


# ============================================================ agency report
@router.get("/workspaces/{wid}/report")
def report(wid: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not plan(user)["reports"]:
        raise HTTPException(403, "Client reports are part of the Business plan.")
    ws = workspace_for(user, wid, db)
    fd = feed(ws.id, user, db)
    watch = watchlist(ws.id, user, db)
    return {"workspace": _ws_out(ws), "generated_at": datetime.utcnow().isoformat(), "feed_date": fd["date"],
            "opportunities": fd["items"][:10], "watchlist": watch, "demo": settings.demo,
            "duty_as_of": load("duty_rates").get("_as_of")}


# ============================================================ billing
@router.post("/billing/checkout")
def checkout(body: CheckoutIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.plan not in ("pro", "business"):
        raise HTTPException(400, "Unknown plan")
    if not settings.stripe_secret_key:
        if settings.is_production:
            raise HTTPException(503, "Billing isn't set up yet")
        user.plan = body.plan  # development only: switch plan instantly to test features
        db.commit()
        return {"url": None, "dev_switched": True, "plan": user.plan}
    import stripe
    stripe.api_key = settings.stripe_secret_key
    price = settings.stripe_price_pro if body.plan == "pro" else settings.stripe_price_business
    s = stripe.checkout.Session.create(mode="subscription", line_items=[{"price": price, "quantity": 1}],
                                       customer_email=user.email, client_reference_id=user.id,
                                       metadata={"plan": body.plan},
                                       success_url=f"{settings.frontend_url}/settings?upgraded=1",
                                       cancel_url=f"{settings.frontend_url}/pricing")
    return {"url": s.url}


@router.post("/billing/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    if not settings.stripe_secret_key:
        raise HTTPException(404, "Billing disabled")
    import stripe
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload, request.headers.get("stripe-signature", ""), settings.stripe_webhook_secret)
    except Exception:
        raise HTTPException(400, "Invalid signature")
    obj = event["data"]["object"]
    if event["type"] == "checkout.session.completed":
        u = db.get(User, obj.get("client_reference_id"))
        if u:
            u.plan = (obj.get("metadata") or {}).get("plan", "pro")
            u.stripe_customer_id = obj.get("customer") or ""
    elif event["type"] == "customer.subscription.deleted":
        u = db.execute(select(User).where(User.stripe_customer_id == obj.get("customer"))).scalar_one_or_none()
        if u:
            u.plan = "free"
    db.commit()

# ============================================================ Autonomous Margin Sentinel
@router.get("/sentinel")
def list_sentinel_products(workspace_id: Optional[str] = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ws = workspace_for(user, workspace_id, db)
    rows = db.execute(select(SentinelProduct).where(SentinelProduct.workspace_id == ws.id).order_by(desc(SentinelProduct.last_scanned_at))).scalars().all()
    
    total_protected = sum(r.retail_price for r in rows)
    critical_threats = len([r for r in rows if r.threat_level == "CRITICAL"])
    warning_threats = len([r for r in rows if r.threat_level == "WARNING"])
    avg_saturation = round(sum(r.saturation_score for r in rows) / len(rows), 1) if rows else 0.0
    
    return {
        "items": [
            {
                "id": r.id,
                "opportunity_id": r.opportunity_id,
                "title": r.title,
                "asin": r.asin,
                "sku": r.sku,
                "retail_price": r.retail_price,
                "supplier_cost": r.supplier_cost,
                "shipping_cost": r.shipping_cost,
                "target_cpa": r.target_cpa,
                "current_cpa": r.current_cpa,
                "saturation_score": r.saturation_score,
                "threat_level": r.threat_level,
                "competitor_count": r.competitor_count,
                "active_ad_count": r.active_ad_count,
                "supplier_status": r.supplier_status,
                "health": r.health,
                "recommendations": r.recommendations,
                "history": r.history,
                "last_scanned_at": r.last_scanned_at.isoformat() if r.last_scanned_at else None,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
        "kpis": {
            "monitored_skus": len(rows),
            "protected_retail_value": round(total_protected, 2),
            "critical_threats": critical_threats,
            "warning_threats": warning_threats,
            "avg_saturation_score": avg_saturation,
        }
    }


@router.post("/sentinel")
def track_sentinel_product(body: SentinelIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    ws = workspace_for(user, body.workspace_id, db)
    o = db.get(Opportunity, body.opportunity_id)
    if not o or not o.data.get("inputs"):
        raise HTTPException(400, "Product must have calculated unit economics")
    
    existing = db.execute(select(SentinelProduct).where(SentinelProduct.workspace_id == ws.id, SentinelProduct.asin == o.asin)).scalar_one_or_none()
    if existing:
        return {"id": existing.id, "already": True}
        
    inputs = dict(o.data["inputs"])
    for k, v in body.overrides.items():
        if k in inputs and v not in (None, ""):
            inputs[k] = float(v) if k != "channel" else v
            
    # Calculate Saturation & Threat Sentinel
    competitors = 6 if settings.demo else 8
    active_ads = 12 if settings.demo else 14
    sat = calculate_saturation_index(competitors, active_ads)
    health = analyze_sentinel_health(inputs, sat, body.target_cpa)
    
    sp = SentinelProduct(
        workspace_id=ws.id,
        opportunity_id=o.id,
        title=o.title,
        asin=o.asin,
        sku=body.sku or f"SKU-{o.asin[:6]}",
        retail_price=inputs["sell"],
        supplier_cost=inputs["supplier"],
        shipping_cost=inputs["ship"],
        target_cpa=health["max_allowable_cpa"],
        current_cpa=health["current_estimated_cpa"],
        saturation_score=sat["score"],
        threat_level=health["threat_level"],
        competitor_count=competitors,
        active_ad_count=active_ads,
        supplier_status="STABLE",
        inputs=inputs,
        health=health,
        recommendations=health["recommendations"],
        history=[{"date": date.today().isoformat(), "cpa_headroom": health["cpa_headroom"], "threat": health["threat_level"]}],
        last_scanned_at=datetime.utcnow()
    )
    db.add(sp)
    db.commit()
    return {"id": sp.id, "threat_level": sp.threat_level}


@router.post("/sentinel/{sid}/scan")
def scan_sentinel_product(sid: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    sp = db.get(SentinelProduct, sid)
    if not sp:
        raise HTTPException(404, "Product not found")
    workspace_for(user, sp.workspace_id, db)
    
    # Recalculate threat analysis
    competitors = max(1, sp.competitor_count + (1 if not settings.demo else 0))
    active_ads = max(2, sp.active_ad_count + (2 if not settings.demo else 0))
    sat = calculate_saturation_index(competitors, active_ads)
    health = analyze_sentinel_health(sp.inputs, sat, sp.current_cpa)
    
    sp.competitor_count = competitors
    sp.active_ad_count = active_ads
    sp.saturation_score = sat["score"]
    sp.threat_level = health["threat_level"]
    sp.health = health
    sp.recommendations = health["recommendations"]
    sp.history = (sp.history or [])[-29:] + [{"date": date.today().isoformat(), "cpa_headroom": health["cpa_headroom"], "threat": health["threat_level"]}]
    sp.last_scanned_at = datetime.utcnow()
    
    db.commit()
    return {"ok": True, "threat_level": sp.threat_level, "health": health}


@router.delete("/sentinel/{sid}")
def remove_sentinel_product(sid: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    sp = db.get(SentinelProduct, sid)
    if not sp:
        raise HTTPException(404, "Product not found")
    workspace_for(user, sp.workspace_id, db)
    db.delete(sp)
    db.commit()
    return {"ok": True}


# ============================================================ admin (development)
@router.post("/admin/run/{what}")
def admin_run(what: str, user: User = Depends(current_user)):
    if settings.is_production:
        raise HTTPException(404, "Not found")
    if what not in ("feed", "watch", "daily"):
        raise HTTPException(400, "Use feed, watch or daily")
    jobs.submit(what)
    return {"queued": what}


@router.get("/admin/feed-runs")
def feed_runs(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(FeedRun).order_by(desc(FeedRun.started_at)).limit(20)).scalars().all()
    return [{"category": r.category, "status": r.status, "candidates": r.candidates, "published": r.published,
             "notes": r.notes, "started_at": r.started_at.isoformat()} for r in rows]
