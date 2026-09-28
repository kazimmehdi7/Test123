"""
Scoute API.  Run:  uvicorn app.main:app --port 8000
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, inspect, select

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


def _run_migrations():
    """
    Bring the schema up to date via Alembic instead of Base.metadata.create_all(), which only
    ever adds missing tables and silently never alters an existing one — any future column/index
    change would just not exist on a deployed DB and 500 the first query that touches it.

    A DB that already has tables from before this migration setup existed (create_all, no
    alembic_version table yet) is stamped at the baseline revision rather than re-run through
    "CREATE TABLE" (which would fail on tables that already exist); anything created fresh runs
    every migration from empty.
    """
    from alembic import command
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    ini_path = os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
    if not os.path.exists(ini_path):
        # Alembic isn't set up in this checkout (e.g. an older clone) — fall back so the app
        # still starts, but this path never applies a migration.
        print("[startup] alembic.ini not found — falling back to create_all (no migration history)")
        Base.metadata.create_all(engine)
        return

    cfg = Config(ini_path)
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "migrations"))
    already_has_tables = inspect(engine).has_table("users")
    if already_has_tables and not inspect(engine).has_table("alembic_version"):
        # Stamp at the baseline revision (not blindly "head") so any migration added *after*
        # baseline still gets applied by the upgrade() call below instead of being skipped.
        baseline = ScriptDirectory.from_config(cfg).get_base()
        print(f"[startup] existing pre-Alembic database detected — stamping baseline {baseline}, not re-creating tables")
        command.stamp(cfg, baseline)
    command.upgrade(cfg, "head")


@app.on_event("startup")
def startup():
    # Register the CAPTCHA solver once at startup
    set_captcha_solver(my_captcha_solver)

    _run_migrations()
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