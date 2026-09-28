# Scoute v2

Every morning: products that still make money after 2026 tariffs, platform fees, ads and returns —
with the most you can pay your supplier, what would stop it making money, and an alert when that changes.

```
scoute/
├── engine/   Python API + data engine (FastAPI, port 8000)
│   ├── app/sources/   Amazon, AliExpress, eBay, brand/IP gate, demo data
│   ├── app/engine/    True Profit, Failure Map, verdict, duty, matching, launch notes
│   ├── app/data/      Editable tables: duty rates, platform fees, return rates, categories
│   ├── app/services.py  Daily feed, search jobs, watchlist recalculation + alerts
│   ├── app/jobs.py      Background worker + daily scheduler
│   └── app/api/         All HTTP endpoints
└── web/      Next.js 14 frontend (port 3000)
```

## Run it (Windows)

**1. Engine** (first time only: create the venv and install)
```powershell
cd engine
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --port 8000
```
Leave it running. On first start it builds today's list in the background.

**2. Web** (second terminal)
```powershell
cd web
npm install
copy .env.local.example .env.local
npm run dev
```
Open http://localhost:3000 and create an account.

Or double-click `start-windows.bat` after the first-time setup.

## Demo mode vs live data

`engine/.env` → `SCOUTE_DEMO=true` (default in `.env.example`) fills the product with clearly
labelled sample data so every screen works without scraping. A banner says "Demo data" everywhere.

For live data set `SCOUTE_DEMO=false`, then:
1. Delete `engine/scoute.db` so demo rows are gone.
2. Check each source from the terminal first (inside `engine/`, venv active):
   ```powershell
   python -m app.tools.check_sources amazon "silicone baking mat"
   python -m app.tools.check_sources movers kitchen
   python -m app.tools.check_sources aliexpress "silicone baking mat"
   python -m app.tools.check_sources full "silicone baking mat"
   ```
   If a source returns 0 results, its page is saved in `engine/debug/` — send that file to fix selectors.
3. Start the API. The daily list builds at `FEED_HOUR_UTC` (default 10 = 6am US Eastern);
   in development you can trigger it from the API: `POST /api/admin/run/feed`.

## What needs keys (all optional)

| Key in `engine/.env` | Turns on |
| --- | --- |
| `PROXY_URL` + `PROXY_ENABLED` | Residential proxy for scraping — **required once deployed** |
| `EBAY_CLIENT_ID` / `EBAY_CLIENT_SECRET` | Resell mode supplier prices (eBay Browse API) |
| `OPENAI_API_KEY` | AI-written ad angles and listing title |
| `STRIPE_SECRET_KEY`, `STRIPE_PRICE_PRO`, `STRIPE_PRICE_BUSINESS`, `STRIPE_WEBHOOK_SECRET` | Real payments. Without it (development only) choosing a plan switches it instantly. |
| `RESEND_API_KEY`, `ALERT_FROM_EMAIL` | Alert emails. Without it alerts stay in the app. |
| `DATABASE_URL` | Postgres instead of SQLite: `docker compose up -d postgres`, then `postgresql+psycopg://postgres:postgres@localhost:5434/scoute` |

## Database & migrations

SQLite (the default `DATABASE_URL`) is for a single-user local demo only — it allows one
writer at a time, so real concurrent traffic (a user's request landing while a background
job writes) throws `database is locked`. Anything beyond solo local use needs Postgres:

```powershell
docker compose up -d postgres
# in engine/.env: DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5434/scoute
```

Schema changes go through Alembic (`engine/migrations/`), not hand edits — the app runs
`alembic upgrade head` on startup automatically, so you never need to run it yourself in normal
use. After changing a model in `app/models.py`, generate the migration and commit it:

```powershell
cd engine
venv\Scripts\activate
alembic revision --autogenerate -m "describe the change"
```

Always read the generated file before committing — autogenerate is a good first draft, not
a guarantee, especially for column renames (it sees those as drop+add and will lose data
unless you edit the migration to use `op.alter_column`/`op.rename_table`).

## Scaling beyond a single machine

- **Scraping worker pool.** `app/fetch.py` used to run each browser profile
  (`stealthy` / `light` / `dynamic`) on exactly one thread — one page load at a time, globally,
  shared across every user's searches and every feed/watchlist/Sentinel refresh. It now runs
  `FETCH_POOL_SIZE` (default 2) independent sessions per profile, round-robined, so that many
  fetches can genuinely run at once. Raise it in `engine/.env` as load grows — but raise
  `PROXY_URLS` (comma-separated) alongside it: more concurrent requests from the same one IP
  gets you blocked faster, not just rate-limited. `PROXY_URL` still works as a single fallback
  proxy for every worker.
- **Job dispatch worker pool.** `app/jobs.py`'s "interactive" queue (user searches) now runs
  `INTERACTIVE_WORKERS` (default 3) threads pulling from the same queue instead of one, so
  dispatch itself isn't a second bottleneck stacked on top of the fetch pool above. The "batch"
  queue (feed/watchlist/Sentinel) stays at `BATCH_WORKERS=1` by default — increase only if you
  understand the advisory-lock behavior below, since two batch workers *in the same process*
  racing the same daily-build check is a different problem from two separate instances doing it.
- **Cross-instance coordination.** Run two+ app instances behind a load balancer (needed at real
  user counts) and each independently decides "it's `FEED_HOUR_UTC`, build the feed" — without
  coordination they'd race to write the same day's rows, or each recalc the watchlist/Sentinel
  and send duplicate alert emails. `app/dlock.py` now takes a Postgres advisory lock around the
  feed build, watchlist recalc, Sentinel recalc, and the daily chain — the loser of the race just
  skips that run instead of duplicating it. This is a no-op on SQLite (nothing to coordinate with
  only one instance possible there). It solves *duplicate runs*, not *job durability* — if an
  instance dies mid-job the work is simply lost until the next scheduled run, and there's still
  no way to distribute the *dispatch* of jobs across instances (each instance only dispatches
  what lands in its own in-memory queue). A real distributed queue (Celery/RQ + Redis — `redis`
  is already in `requirements.txt` but unused) is the next step if you need work to survive an
  instance restart or want jobs load-balanced rather than duplicated-and-locked-out.

## Auth & accounts

- **Email verification** — registering creates the account immediately (nothing blocks login
  on it yet, by design: enforcing it before you've confirmed `RESEND_API_KEY` actually delivers
  would just lock people out) and sends a verify link. `POST /auth/resend-verification` from
  Settings gets a new one. Without `RESEND_API_KEY` set, the register/resend response includes
  `dev_verify_token` (never in production) so the flow is testable without email infra.
- **Password reset** — `/forgot-password` → `/reset-password?token=...`, 1-hour-lived
  single-use tokens (`auth_tokens` table, only the SHA-256 hash is stored). The forgot-password
  response is identical whether or not the email exists, so the endpoint can't be used to check
  who has an account. A successful reset bumps the user's `token_version`, which immediately
  invalidates every JWT issued before it — including on other devices. `POST /auth/logout-all`
  does the same bump on demand ("I think my session leaked") without changing the password.
- **Rate limiting** on `/auth/login`, `/auth/register`, `/auth/forgot-password`,
  `/auth/resend-verification` (`app/ratelimit.py`) — in-memory, per process. With one app
  instance this is a real limit; with several behind a load balancer each instance counts
  independently, so the effective limit scales with instance count. Fine as a first line of
  defense against a single-source script; put a proxy/WAF-level limiter in front for a hard
  guarantee once you're running more than one instance.

## Before launch — verify these by hand

- `engine/app/data/duty_rates.json` — rows with `"verified": false` are category estimates.
- `engine/app/data/channel_fees.json` — check each platform's current fee page.
- `engine/app/data/return_rates.json`, `affiliate_rates.json` — estimates.
- Live selectors for Amazon Movers & Shakers and AliExpress (run `check_sources`).
- The Sentinel's competitor/ad counts (`app/engine/sentinel.py`) are a bounded, seeded
  *estimate*, not a live feed — there's no Meta/TikTok ad-library or storefront-scraping
  integration behind them yet. Fine as a directional signal; don't market it as live data
  until that integration exists.
- `JWT_SECRET` must be a real random 32+ character value in production — the app now refuses
  to start otherwise (`app/config.py`), but double-check it's actually set in your deploy env.

These files are plain JSON: edit them and restart; no code changes.

## Plans

| | Free | Pro $15 | Business $59 |
| --- | --- | --- | --- |
| Daily list | top 3 with full math | all | all |
| Product checks / day | 5 | 100 | 500 |
| Edit numbers | — | yes | yes |
| Watchlist + alerts | — | 25 | 200 |
| Margin Sentinel | — | 10 | 100 |
| Client workspaces + reports | — | — | 5 |

Limits live in `engine/app/config.py` → `PLANS`.
