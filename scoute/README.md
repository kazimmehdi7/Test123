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
| `DATABASE_URL` | Postgres instead of SQLite, e.g. `postgresql+psycopg://postgres:postgres@localhost:5433/scoute` (`pip install psycopg[binary]`) |

## Before launch — verify these by hand

- `engine/app/data/duty_rates.json` — rows with `"verified": false` are category estimates.
- `engine/app/data/channel_fees.json` — check each platform's current fee page.
- `engine/app/data/return_rates.json`, `affiliate_rates.json` — estimates.
- Live selectors for Amazon Movers & Shakers and AliExpress (run `check_sources`).

These files are plain JSON: edit them and restart; no code changes.

## Plans

| | Free | Pro $15 | Business $59 |
| --- | --- | --- | --- |
| Daily list | top 3 with full math | all | all |
| Product checks / day | 5 | 100 | 500 |
| Edit numbers | — | yes | yes |
| Watchlist + alerts | — | 25 | 200 |
| Client workspaces + reports | — | — | 5 |

Limits live in `engine/app/config.py` → `PLANS`.
