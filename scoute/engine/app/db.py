from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

_is_sqlite = settings.database_url.startswith("sqlite")
_connect_args = {"check_same_thread": False, "timeout": 30} if _is_sqlite else {}
engine = create_engine(settings.database_url, connect_args=_connect_args, pool_pre_ping=True)

if _is_sqlite:
    # SQLite's default rollback-journal mode lets only one writer touch the file at a time,
    # so with several requests + the background workers writing concurrently you get
    # "database is locked" errors under normal load — even at modest user counts.
    # WAL lets readers and a writer run concurrently; busy_timeout makes writers that do
    # collide wait instead of failing immediately.
    # This buys headroom, it does not make SQLite fit for ~20k concurrent users —
    # see README "Scaling beyond a single SQLite file" for when to move to DATABASE_URL=postgresql+...
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA busy_timeout=30000")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
