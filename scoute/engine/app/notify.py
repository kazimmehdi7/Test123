"""Alert emails through Resend. Without RESEND_API_KEY, alerts stay in-app only."""
from __future__ import annotations

import httpx

from .config import settings


async def send_alert_email(to: str, subject: str, body: str) -> bool:
    if not settings.resend_api_key:
        return False
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post("https://api.resend.com/emails",
                             headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                             json={"from": settings.alert_from_email, "to": [to], "subject": subject,
                                   "text": f"{body}\n\nOpen Scoute: {settings.frontend_url}/watchlist"})
        return r.status_code < 300
    except Exception:
        return False
