from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Register(BaseModel):
    email: str
    password: str = Field(min_length=8)
    name: str = ""


class Login(BaseModel):
    email: str
    password: str


class SettingsIn(BaseModel):
    ad_cost_pct: Optional[float] = Field(None, ge=0, le=0.8)
    target_profit_pct: Optional[float] = Field(None, ge=0, le=0.8)
    buffer_pct: Optional[float] = Field(None, ge=0, le=0.3)
    us_warehouse_premium: Optional[float] = Field(None, ge=0, le=2)
    alert_email: Optional[bool] = None
    name: Optional[str] = None


class Brief(BaseModel):
    mode: str = "dropship"            # dropship / resell / affiliate
    market: str = "US"                # US / EU
    channel: str = "shopify"          # shopify / amazon / tiktok_shop / ebay
    sourcing: str = "china"           # china / us_warehouse
    categories: List[str] = []
    price_min: float = 10
    price_max: float = 60
    budget: float = 500
    min_margin: float = 0.15
    min_profit: float = 3


class WorkspaceIn(BaseModel):
    name: str
    client_name: str = ""
    logo_url: str = ""


class SearchIn(BaseModel):
    query: str = Field(min_length=2, max_length=200)
    mode: str = "dropship"


class RecalcIn(BaseModel):
    overrides: Dict[str, Any] = {}


class WatchIn(BaseModel):
    opportunity_id: str
    workspace_id: Optional[str] = None
    overrides: Dict[str, Any] = {}


class CheckoutIn(BaseModel):
    plan: str


class SentinelIn(BaseModel):
    opportunity_id: str
    workspace_id: Optional[str] = None
    sku: Optional[str] = ""
    target_cpa: Optional[float] = None
    overrides: Dict[str, Any] = {}

