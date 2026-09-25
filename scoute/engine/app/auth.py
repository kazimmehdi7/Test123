from __future__ import annotations

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


def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def check_pw(pw: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), h.encode())
    except ValueError:
        return False


def token_for(user: User) -> str:
    return jwt.encode({"sub": user.id, "exp": int(time.time()) + 60 * 60 * 24 * 30}, settings.jwt_secret, algorithm="HS256")


def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not creds:
        raise HTTPException(401, "Log in to continue")
    try:
        uid = jwt.decode(creds.credentials, settings.jwt_secret, algorithms=["HS256"])["sub"]
    except jwt.PyJWTError:
        raise HTTPException(401, "Your session expired. Log in again.")
    user = db.get(User, uid)
    if not user:
        raise HTTPException(401, "Account not found")
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
