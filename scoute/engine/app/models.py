from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def _id() -> str:
    return uuid.uuid4().hex


DEFAULT_USER_SETTINGS = {
    "ad_cost_pct": 0.20,        # ad spend per sale, share of selling price
    "target_profit_pct": 0.15,  # profit the user wants to keep per sale
    "buffer_pct": 0.05,         # uncertainty buffer
    "us_warehouse_premium": 0.30,
    "alert_email": True,
}


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    plan: Mapped[str] = mapped_column(String(20), default="free")
    stripe_customer_id: Mapped[str] = mapped_column(String(80), default="")
    settings: Mapped[dict] = mapped_column(JSON, default=lambda: dict(DEFAULT_USER_SETTINGS))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    client_name: Mapped[str] = mapped_column(String(120), default="")
    logo_url: Mapped[str] = mapped_column(String(500), default="")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    brief: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Opportunity(Base):
    """One analysed product. Feed rows (origin='feed') and search results (origin='search')."""
    __tablename__ = "opportunities"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    origin: Mapped[str] = mapped_column(String(10), default="feed")
    category: Mapped[str] = mapped_column(String(40), index=True)
    feed_date: Mapped[date] = mapped_column(Date, index=True, default=date.today)
    mode: Mapped[str] = mapped_column(String(12), default="dropship")
    asin: Mapped[str] = mapped_column(String(20), index=True, default="")
    title: Mapped[str] = mapped_column(String(500))
    image_url: Mapped[str] = mapped_column(String(800), default="")
    action: Mapped[str] = mapped_column(String(16), index=True)
    net_profit: Mapped[float] = mapped_column(Float, default=0.0)
    margin: Mapped[float] = mapped_column(Float, default=0.0)
    sell_price: Mapped[float] = mapped_column(Float, default=0.0)
    safety: Mapped[str] = mapped_column(String(10), default="LOW")
    rank_score: Mapped[float] = mapped_column(Float, default=0.0)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FeedRun(Base):
    __tablename__ = "feed_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(40), index=True)
    feed_date: Mapped[date] = mapped_column(Date, default=date.today)
    status: Mapped[str] = mapped_column(String(20), default="running")
    candidates: Mapped[int] = mapped_column(Integer, default=0)
    published: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class SearchJob(Base):
    __tablename__ = "search_jobs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    query: Mapped[str] = mapped_column(String(300))
    mode: Mapped[str] = mapped_column(String(12), default="dropship")
    status: Mapped[str] = mapped_column(String(12), default="queued")  # queued/running/done/failed
    progress: Mapped[str] = mapped_column(String(200), default="Waiting to start")
    result_ids: Mapped[list] = mapped_column(JSON, default=list)
    sources: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WatchItem(Base):
    __tablename__ = "watch_items"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    opportunity_id: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(500))
    asin: Mapped[str] = mapped_column(String(20), default="")
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)   # the numbers we recalculate from
    last_result: Mapped[dict] = mapped_column(JSON, default=dict)
    history: Mapped[list] = mapped_column(JSON, default=list)  # [{date, net, action}]
    last_checked: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("workspace_id", "opportunity_id"),)


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    watch_id: Mapped[str] = mapped_column(String(32), default="")
    kind: Mapped[str] = mapped_column(String(20))  # destroyed/weakened/improved/tariff/supplier
    title: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text, default="")
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Usage(Base):
    __tablename__ = "usage"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    day: Mapped[date] = mapped_column(Date, default=date.today)
    searches: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (UniqueConstraint("user_id", "day"),)


class SentinelProduct(Base):
    """Product monitored by the Autonomous Margin Sentinel & Competitor Radar."""
    __tablename__ = "sentinel_products"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    opportunity_id: Mapped[str] = mapped_column(String(32), default="")
    title: Mapped[str] = mapped_column(String(500))
    asin: Mapped[str] = mapped_column(String(20), default="")
    sku: Mapped[str] = mapped_column(String(50), default="")
    retail_price: Mapped[float] = mapped_column(Float, default=0.0)
    supplier_cost: Mapped[float] = mapped_column(Float, default=0.0)
    shipping_cost: Mapped[float] = mapped_column(Float, default=0.0)
    target_cpa: Mapped[float] = mapped_column(Float, default=0.0)
    current_cpa: Mapped[float] = mapped_column(Float, default=0.0)
    saturation_score: Mapped[float] = mapped_column(Float, default=0.0)
    threat_level: Mapped[str] = mapped_column(String(20), default="STABLE")  # STABLE / WARNING / CRITICAL / THRIVING
    competitor_count: Mapped[int] = mapped_column(Integer, default=0)
    active_ad_count: Mapped[int] = mapped_column(Integer, default=0)
    supplier_status: Mapped[str] = mapped_column(String(40), default="STABLE")
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    health: Mapped[dict] = mapped_column(JSON, default=dict)
    recommendations: Mapped[list] = mapped_column(JSON, default=list)
    history: Mapped[list] = mapped_column(JSON, default=list)
    last_scanned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("workspace_id", "asin"),)
