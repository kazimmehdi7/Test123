"""eBay official Browse API (needs EBAY_CLIENT_ID / EBAY_CLIENT_SECRET)."""
from __future__ import annotations

import base64
import time
from typing import List, Optional

from ..config import settings
from ..fetch import http
from ..listing import SUPPLY, Listing

_token: dict = {"value": None, "exp": 0.0}


def enabled() -> bool:
    return bool(settings.ebay_client_id and settings.ebay_client_secret)


async def _get_token() -> Optional[str]:
    if _token["value"] and time.time() < _token["exp"] - 60:
        return _token["value"]
    basic = base64.b64encode(f"{settings.ebay_client_id}:{settings.ebay_client_secret}".encode()).decode()
    r = await http("POST", "https://api.ebay.com/identity/v1/oauth2/token",
                   headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"},
                   data={"grant_type": "client_credentials", "scope": "https://api.ebay.com/oauth/api_scope"})
    if r.status_code != 200:
        print(f"[ebay] token failed {r.status_code}")
        return None
    j = r.json()
    _token.update(value=j["access_token"], exp=time.time() + float(j.get("expires_in", 7200)))
    return _token["value"]


async def search(query: str, limit: int = 6) -> List[Listing]:
    token = await _get_token()
    if not token:
        return []
    r = await http("GET", "https://api.ebay.com/buy/browse/v1/item_summary/search",
                   params={"q": query, "limit": limit, "filter": "buyingOptions:{FIXED_PRICE},conditions:{NEW}"},
                   headers={"Authorization": f"Bearer {token}", "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"})
    if r.status_code != 200:
        print(f"[ebay] search failed {r.status_code}")
        return []
    out: List[Listing] = []
    for it in r.json().get("itemSummaries", []):
        price = float(it.get("price", {}).get("value") or 0) or None
        ship = None
        opts = it.get("shippingOptions") or []
        if opts and opts[0].get("shippingCost"):
            ship = float(opts[0]["shippingCost"].get("value") or 0)
        out.append(Listing(source="ebay", side=SUPPLY, source_id=it.get("itemId", ""), title=it.get("title", ""),
                           url=it.get("itemWebUrl", ""), price=price, shipping_cost=ship,
                           image_url=(it.get("image") or {}).get("imageUrl"),
                           raw={"seller_feedback": (it.get("seller") or {}).get("feedbackPercentage")}))
    return out
