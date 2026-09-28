"""
Scoute API.  Run:  uvicorn app.main:app --port 8000
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from . import jobs
from .api.routes import router
from .config import settings
from .db import Base, SessionLocal, engine
from .fetch import close_all
from .models import Opportunity

# ────────────────────────────────────────────────
# CAPTCHA solver hook
# ────────────────────────────────────────────────
from .sources.aliexpress import set_captcha_solver


app = FastAPI(title="Scoute API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


# ────────────────────────────────────────────────
# CAPTCHA solver (skeleton – replace with real logic later)
# ────────────────────────────────────────────────
async def my_captcha_solver(page) -> bool:
    """
    Skeleton CAPTCHA solver.
    Replace the body with real 2Captcha / CapSolver logic when ready.

    Must return:
        True  → CAPTCHA was solved successfully
        False → failed to solve
    """
    # 1. Detect that a slider / challenge is present
    # 2. Extract sitekey or challenge image / data
    # 3. Call your solver API
    # 4. Inject the solution token back into the page
    # 5. Wait for navigation / success indicator
    # 6. Return True if solved, False otherwise
    return False


@app.on_event("startup")
def startup():
    # Register the CAPTCHA solver once at startup
    set_captcha_solver(my_captcha_solver)

    Base.metadata.create_all(engine)
    jobs.start()

    with SessionLocal() as db:
        has_feed = db.execute(
            select(func.count())
            .select_from(Opportunity)
            .where(Opportunity.origin == "feed")
        ).scalar()

    if not has_feed:
        print("[startup] no feed yet — building it now in the background")
        jobs.submit("feed")

    print(
        f"[startup] Scoute API ready | demo={settings.demo} "
        f"| db={settings.database_url.split('://')[0]}"
    )


@app.on_event("shutdown")
async def shutdown():
    await close_all()  # close browser sessions cleanly when the server stops