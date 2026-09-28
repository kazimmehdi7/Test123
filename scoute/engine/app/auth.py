from __future__ import annotations

import hashlib
import secrets
import time
from datetime import date

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import PLANS, settings
from .db import get_db
from .models import Usage, User, Workspace

bearer = HTTPBearer(auto_error=False)


def new_token() -> tuple[str, str]:
    """For email-verify / password-reset links: (raw token to email out, sha256 hash to store).
    Only the hash is ever persisted — see AuthToken's docstring."""
    raw = secrets.token_urlsafe(32)
    return raw, hashlib.sha256(raw.encode()).hexdigest()


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def check_pw(pw: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), h.encode())
    except ValueError:
        return False


def token_for(user: User) -> str:
    return jwt.encode({"sub": user.id, "tv": user.token_version, "exp": int(time.time()) + 60 * 60 * 24 * 30},
                      settings.jwt_secret, algorithm="HS256")


def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not creds:
        raise HTTPException(401, "Log in to continue")
    try:
        payload = jwt.decode(creds.credentials, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Your session expired. Log in again.")
    user = db.get(User, payload["sub"])
    if not user:
        raise HTTPException(401, "Account not found")
    # A token issued before this column existed carries no "tv" claim — treat that as tv=0,
    # which matches every existing user's default, so this doesn't force anyone to re-login.
    # A mismatch means the password was reset or "log out everywhere" was used since this
    # token was issued: the token is old, even though it hasn't hit its 30-day expiry yet.
    if payload.get("tv", 0) != user.token_version:
        raise HTTPException(401, "Your session was signed out. Log in again.")
    return user


def plan(user: User) -> dict:
    return PLANS.get(user.plan, PLANS["free"])


def workspace_for(user: User, workspace_id: str | None, db: Session) -> Workspace:
    q = select(Workspace).where(Workspace.owner_id == user.id)
    q = q.where(Workspace.id == workspace_id) if workspace_id else q.where(Workspace.is_default == True)  # noqa: E712
    ws = db.execute(q).scalar_one_or_none()
    if not ws:
        raise HTTPException(404, "Workspace not found")
    return ws


def use_search(user: User, db: Session):
    today = date.today()
    row = db.execute(select(Usage).where(Usage.user_id == user.id, Usage.day == today)).scalar_one_or_none()
    if not row:
        row = Usage(user_id=user.id, day=today, searches=0)
        db.add(row)
    limit = plan(user)["searches_per_day"]
    if row.searches >= limit:
        raise HTTPException(429, f"You've used all {limit} searches for today on the {user.plan.title()} plan.")
    row.searches += 1
    db.commit()
    return limit - row.searches
