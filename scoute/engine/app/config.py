"""All settings come from .env. Missing optional keys switch a feature off; nothing crashes."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def _get(key: str, default: str = "") -> str:
    return (os.getenv(key) or default).strip()


def _bool(key: str, default: str = "false") -> bool:
    return _get(key, default).lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    database_url: str = _get("DATABASE_URL", "sqlite:///./scoute.db")
    jwt_secret: str = _get("JWT_SECRET", "dev-secret-change-me")
    frontend_url: str = _get("FRONTEND_URL", "http://localhost:3000")
    environment: str = _get("ENVIRONMENT", "development")
    demo: bool = _bool("SCOUTE_DEMO", "false")
    amazon_tag: str = _get("AMAZON_ASSOCIATE_TAG", "placeholder")
    proxy_url: str = _get("PROXY_URL")
    # Optional: comma-separated list of proxies to spread the fetch worker pool across
    # (e.g. several residential-proxy exit sessions), so raising FETCH_POOL_SIZE doesn't just
    # mean more concurrent requests from the same one IP. Falls back to PROXY_URL for all
    # workers when unset.
    proxy_urls: List[str] = field(default_factory=lambda: [
        p.strip() for p in _get("PROXY_URLS").split(",") if p.strip()
    ])
    ebay_client_id: str = _get("EBAY_CLIENT_ID")
    ebay_client_secret: str = _get("EBAY_CLIENT_SECRET")
    feed_categories: List[str] = field(default_factory=lambda: [
        c.strip() for c in _get("FEED_CATEGORIES", "kitchen,home,pet,beauty,fitness,outdoor,office,baby").split(",") if c.strip()
    ])
    feed_hour_utc: int = int(_get("FEED_HOUR_UTC", "10"))
    openai_api_key: str = _get("OPENAI_API_KEY")
    stripe_secret_key: str = _get("STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = _get("STRIPE_WEBHOOK_SECRET")
    stripe_price_pro: str = _get("STRIPE_PRICE_PRO")
    stripe_price_business: str = _get("STRIPE_PRICE_BUSINESS")
    resend_api_key: str = _get("RESEND_API_KEY")
    alert_from_email: str = _get("ALERT_FROM_EMAIL", "alerts@example.com")

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()

if settings.is_production and (settings.jwt_secret in ("dev-secret-change-me", "change-me-to-a-long-random-string") or len(settings.jwt_secret) < 32):
    # A predictable/short JWT secret in production lets anyone forge a login token for any
    # user id. Fail loudly at startup rather than silently issuing forgeable sessions.
    raise RuntimeError(
        "ENVIRONMENT=production but JWT_SECRET is missing/default/too short. "
        "Set JWT_SECRET to a random string of 32+ characters before starting in production."
    )

PLANS = {
    "free":     {"searches_per_day": 5,   "feed_items": 3,   "watch_items": 0,   "sentinel_items": 0,  "workspaces": 1, "full_detail": False, "reports": False},
    "pro":      {"searches_per_day": 100, "feed_items": 999, "watch_items": 25,  "sentinel_items": 10, "workspaces": 1, "full_detail": True,  "reports": False},
    "business": {"searches_per_day": 500, "feed_items": 999, "watch_items": 200, "sentinel_items": 100, "workspaces": 5, "full_detail": True,  "reports": True},
}
