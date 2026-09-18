# Paylio

> **Personal Finance Tracker with AI-Driven Insights**
> Full-stack Django application with a React Native mobile client, AI-powered spending advisor, live metal rate tracking, and broker portfolio integration.

---

## Table of Contents

1. [Overview](#overview)
2. [Feature Set](#feature-set)
3. [Architecture](#architecture)
4. [Technology Stack](#technology-stack)
5. [Project Structure](#project-structure)
6. [Prerequisites](#prerequisites)
7. [Local Development Setup](#local-development-setup)
8. [Environment Variables](#environment-variables)
9. [Running the Application](#running-the-application)
10. [Running Tests](#running-tests)
11. [Mobile App](#mobile-app)
12. [REST API Reference](#rest-api-reference)
13. [Background Jobs](#background-jobs)
14. [Docker Deployment](#docker-deployment)
15. [Security Considerations](#security-considerations)
16. [Contributing](#contributing)

---

## Overview

Paylio is a self-hosted personal finance platform built for the Indian market. It combines
transaction management, budget tracking, rule-based financial insights, LLM-generated advice,
precious metal rate monitoring, and Zerodha portfolio sync into a single cohesive system.

The web interface is server-rendered Django with HTMX for reactive partial updates — no page
reloads for table filtering, advisor feed refreshes, or budget progress. A companion React Native
/ Expo mobile app communicates with the same backend through a versioned JSON REST API.

---

## Feature Set

### Transactions
- Manual entry and CSV bank statement import
- Three-tier automatic categorisation:
  1. **User overrides** — remembered per merchant, applied immediately
  2. **Keyword rules** — fast in-process matching for common merchants (Swiggy, Uber, Amazon, etc.)
  3. **LLM fallback** — async Celery task sends the merchant name to a locally-hosted `qwen3:14b` via Ollama
- One-click recategorisation from the transaction table updates the merchant memory
- Duplicate detection via `external_id` unique constraint per account

### Budgets
- Per-category monthly spending limits
- Live progress bar updated in real-time via HTMX (Redis-cached, 5-minute TTL)

### Advisor Feed
- Rule-based insight engine runs nightly and on demand:
  - **Budget Overspend** — fires when current-month spending exceeds a limit
  - **Trend Increase** — fires when spending is >30% above the trailing 3-month average
- Each insight triggers an Ollama LLM call to generate 2-4 sentences of personalised coaching advice
- Push notifications to mobile devices for `CRITICAL` severity insights (Expo Push API)

### Precious Metal Rates
- Gold, Silver, and Platinum prices fetched from GoldAPI.io every 30 minutes
- Displayed in all standard Indian purities (24K, 22K, 18K for gold; 999, 925 for silver; 950, 900 for platinum)

### Investments
- Zerodha Kite Connect integration — OAuth token exchange and nightly holdings sync
- Portfolio P&L calculation (current value vs average cost basis)
- Daily `PortfolioSnapshot` for historical tracking
- 2FA (TOTP) required to connect a broker account

### Security
- Custom `User` model for forward-compatible schema evolution
- TOTP two-factor authentication with QR code setup (`django-otp`)
- Brute-force protection — account lockout after 5 failed logins (`django-axes`)
- Field-level encryption for broker tokens and bank consent metadata (Fernet symmetric encryption)
- JWT authentication for the REST API (access: 1h, refresh: 14d, rotation enabled)
- HTTPS-only cookies, HSTS, and CSP headers in production

### Open Banking (Setu AA)
- Account Aggregator consent flow for fetching bank statement data
- Consent metadata stored encrypted at rest
- Webhook receiver with HMAC-SHA256 signature verification

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Client Layer                               │
│                                                                     │
│   Browser (HTMX + Alpine.js + Chart.js)    React Native / Expo App │
│         ↕ HTML partials / SSR                    ↕ JSON REST API   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────────┐
│                       Django Application                            │
│                                                                     │
│  accounts │ transactions │ budgets │ advisor │ investments │ rates  │
│  integrations │ dashboard │ api                                     │
│                                                                     │
│  ┌──────────────┐   ┌────────────────┐   ┌──────────────────────┐  │
│  │  Web Views   │   │  REST API v1   │   │   Admin Interface    │  │
│  │ (HTMX/SSR)  │   │  (DRF + JWT)   │   │   /admin/            │  │
│  └──────────────┘   └────────────────┘   └──────────────────────┘  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
        ┌────────────────────┼───────────────────┐
        │                    │                   │
┌───────▼──────┐   ┌─────────▼──────┐   ┌───────▼──────────┐
│  PostgreSQL  │   │  Redis         │   │  Ollama           │
│  (primary DB)│   │  DB0: Celery   │   │  qwen3:14b        │
│              │   │  DB1: Cache    │   │  (LLM inference)  │
└──────────────┘   └────────────────┘   └──────────────────┘
                             │
              ┌──────────────┼─────────────────┐
              │              │                 │
   ┌──────────▼───┐  ┌──────▼──────┐  ┌──────▼────────┐
   │ Celery Worker│  │ Celery Worker│  │ Celery Beat    │
   │ (default Q)  │  │ (llm Q)      │  │ (scheduler)    │
   └──────────────┘  └─────────────┘  └────────────────┘
```

### Key Design Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Frontend interaction | HTMX + Alpine.js | No full SPA build step; partial HTML swaps for dynamic UI |
| LLM deployment | Ollama (self-hosted) | Privacy-first; no external API calls for financial data |
| Task queue | Celery with two queues | `default` for sync-sensitive tasks; `llm` for slow Ollama calls (c=1) |
| Cache | django-redis on Redis DB1 | Multi-worker safe; dashboard and budget progress cached 5 min |
| Field encryption | Fernet (symmetric) | Encrypts broker tokens and consent metadata at rest |
| Mobile auth | JWT (simplejwt) | Stateless; coexists with session auth for the web UI |
| DB | PostgreSQL only | JSONField, partial UniqueConstraint, and JSONB semantics required |

---

## Technology Stack

### Backend
| Layer | Technology | Version |
|-------|-----------|---------|
| Framework | Django | 5.1.x |
| Database | PostgreSQL | 16 |
| Cache / Broker | Redis | 7 |
| Task Queue | Celery | 5.4 |
| Beat Scheduler | django-celery-beat | 2.7 |
| REST API | Django REST Framework | 3.15 |
| JWT | djangorestframework-simplejwt | 5.3 |
| 2FA | django-otp | 1.5 |
| Brute-force | django-axes | 6.5 |
| Field Encryption | cryptography (Fernet) | 42 |
| Static Files | WhiteNoise | 6.7 |
| WSGI Server | Gunicorn | 22 |
| HTMX | htmx.js | vendored |
| LLM | Ollama (`qwen3:14b`) | — |

### Mobile
| Layer | Technology | Version |
|-------|-----------|---------|
| Framework | React Native / Expo | 0.74 / ~51 |
| Navigation | React Navigation | 6 |
| Data Fetching | TanStack React Query | 5 |
| Auth Storage | expo-secure-store | 13 |
| Push Notifications | expo-notifications | 0.28 |
| Charts | react-native-chart-kit | 6 |

### Testing
| Tool | Purpose |
|------|---------|
| pytest + pytest-django | Backend test runner |
| factory_boy | Test fixture factories |
| responses | HTTP call mocking |
| freezegun | Date/time freezing |
| pytest-mock | Mock/patch helpers |
| Jest | Mobile unit tests |
| @testing-library/react-native | Component tests |

---

## Project Structure

```
Paylio/
├── config/                  # Django project config
│   ├── settings.py          # All settings, reads from .env via python-decouple
│   ├── urls.py              # Root URL dispatcher
│   ├── celery.py            # Celery application factory
│   └── wsgi.py
│
├── accounts/                # Custom User model, auth views, TOTP 2FA
├── transactions/            # Category, FinancialAccount, Transaction models
│   ├── categorization.py    # Three-tier categorisation engine (single source of truth)
│   ├── importers.py         # CSV bank statement importer
│   └── tests/
│
├── budgets/                 # Budget model, progress service, HTMX partial
├── advisor/                 # Insight model, rule engine, Ollama AI, Celery tasks
│   ├── rules.py             # BudgetOverspendRule, TrendIncreaseRule
│   ├── ai.py                # Ollama HTTP client (generate_advice, categorize_via_llm)
│   └── tasks.py             # run_daily_insights, categorize_with_llm (Celery)
│
├── dashboard/               # Aggregation service, dashboard view
│   └── services.py          # get_monthly_summary() — shared by web and API
│
├── integrations/            # BankConsent model, Fernet field, Setu AA, Kite broker
│   ├── fields.py            # EncryptedTextField (Fernet)
│   └── brokers/kite.py      # Zerodha Kite Connect wrapper
│
├── investments/             # BrokerConnection, Holding, PortfolioSnapshot; sync tasks
├── rates/                   # MetalRateSnapshot, GoldAPI fetcher, purity calculator
├── api/                     # REST API v1 — serializers, viewsets, JWT, push notifications
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── notifications.py     # Expo Push API dispatcher
│
├── templates/               # Django HTML templates
│   ├── base.html            # Dark Tailwind shell (Slate palette)
│   ├── partials/            # HTMX partial fragments
│   └── {app}/               # Per-app full-page templates
│
├── static/                  # CSS (Tailwind compiled), vendored JS (htmx, alpine, chart.js)
├── mobile/                  # React Native / Expo mobile application
│   ├── App.tsx              # Root: QueryClient + AuthProvider + TabNavigator
│   └── src/
│       ├── api/             # Typed API client hooks (react-query)
│       ├── auth/            # AuthContext + SecureStore token management
│       ├── navigation/      # TabNavigator
│       └── screens/         # Dashboard, Transactions, Advisor, Rates screens
│
├── Dockerfile               # Python 3.12-slim image for web + workers
├── docker-compose.yml       # db, redis, ollama, web, celery_default, celery_llm, celery_beat
├── entrypoint.sh            # migrate + collectstatic before gunicorn starts
├── pytest.ini               # DJANGO_SETTINGS_MODULE, --nomigrations
├── conftest.py              # CELERY_TASK_ALWAYS_EAGER autouse fixture
├── requirements.txt         # All Python dependencies (pinned major versions)
└── .env.example             # Template for all required environment variables
```

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.12+ | |
| PostgreSQL | 15+ | Do not use SQLite — JSON fields behave differently |
| Redis | 7+ | Used for both Celery broker (DB0) and cache (DB1) |
| Node.js | 18+ | Only needed for mobile app development |
| Ollama | latest | Required for LLM categorisation and advisor advice |

---

## Local Development Setup

### 1. Clone and create virtual environment

```bash
git clone <repo-url>
cd Paylio
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` — at minimum set:

```ini
SECRET_KEY=your-secret-key-here          # 50+ random chars
DEBUG=True
DB_NAME=spendtracker
DB_USER=spendtracker
DB_PASSWORD=your-db-password
DB_HOST=127.0.0.1
DB_PORT=5432                             # or 5433 if using docker-compose
REDIS_URL=redis://localhost:6379/0
CACHE_URL=redis://localhost:6379/1
OLLAMA_HOST=http://localhost:11434
FIELD_ENCRYPTION_KEY=                    # generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 4. Set up PostgreSQL database

```bash
# Using psql
createdb spendtracker
createuser spendtracker
psql -c "ALTER USER spendtracker PASSWORD 'your-db-password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE spendtracker TO spendtracker;"
```

Or start the database via Docker:

```bash
docker-compose up -d db redis
```

### 5. Run migrations

```bash
python manage.py migrate
```

### 6. Create a superuser

```bash
python manage.py createsuperuser
```

### 7. Pull the LLM model (optional — required for AI advice)

```bash
# Start Ollama (if not already running)
ollama serve

# Pull the model used by the advisor
ollama pull qwen3:14b
```

---

## Environment Variables

All settings are read from `.env` via `python-decouple`. Sensible defaults are provided for
development but **must be explicitly set in production**.

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✅ | Django secret key — generate a fresh one for production |
| `DEBUG` | ✅ | `True` in development, `False` in production |
| `ALLOWED_HOSTS` | ✅ | Comma-separated list of valid hostnames |
| `DB_NAME` | ✅ | PostgreSQL database name |
| `DB_USER` | ✅ | PostgreSQL username |
| `DB_PASSWORD` | ✅ | PostgreSQL password |
| `DB_HOST` | ✅ | PostgreSQL host (use `db` inside Docker) |
| `DB_PORT` | ✅ | PostgreSQL port (default `5432`) |
| `REDIS_URL` | ✅ | Celery broker URL — e.g. `redis://localhost:6379/0` |
| `CACHE_URL` | ✅ | Django cache URL — e.g. `redis://localhost:6379/1` |
| `OLLAMA_HOST` | ✅ | Ollama API base URL — e.g. `http://localhost:11434` |
| `FIELD_ENCRYPTION_KEY` | ✅ | Fernet key for encrypting broker tokens at rest |
| `METALS_API_KEY` | ⚠️ | GoldAPI.io API key — required for live metal prices |
| `KITE_API_KEY` | ⚠️ | Zerodha Kite Connect API key |
| `KITE_API_SECRET` | ⚠️ | Zerodha Kite Connect API secret |
| `SETU_CLIENT_ID` | ⚠️ | Setu Account Aggregator client ID |
| `SETU_CLIENT_SECRET` | ⚠️ | Setu Account Aggregator client secret |
| `SETU_AA_BASE_URL` | ⚠️ | Setu AA base URL (sandbox or production) |
| `SETU_WEBHOOK_SECRET` | ⚠️ | HMAC-SHA256 secret for verifying Setu webhook posts |

> ✅ Required always &nbsp;&nbsp; ⚠️ Required for the specific integration feature

---

## Running the Application

### Development server

```bash
# Terminal 1 — Django dev server
python manage.py runserver

# Terminal 2 — Celery default worker (transactions, broker sync, metal rates)
celery -A config worker -l info -Q default -c 4

# Terminal 3 — Celery LLM worker (advisor AI, categorisation — single concurrency)
celery -A config worker -l info -Q llm -c 1

# Terminal 4 — Celery beat scheduler (nightly insights, rate refresh, holdings sync)
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

The application will be available at `http://127.0.0.1:8000`.

### Compile Tailwind CSS (after template changes)

```bash
npx tailwindcss -i ./static/src/input.css -o ./static/css/main.css --watch
```

---

## Running Tests

### Backend (pytest)

```bash
# All tests with coverage report
pytest --cov=. --cov-report=term-missing -q

# Single app
pytest accounts/ -v

# Single test file
pytest transactions/tests/test_categorization.py -v
```

Tests run with `--nomigrations` (fast schema creation) and `CELERY_TASK_ALWAYS_EAGER=True`
(tasks execute synchronously inline — no broker required).

**Current coverage**: 106 tests across all apps pass.

### Mobile (Jest)

```bash
cd mobile
npm test
# or watch mode
npm test -- --watch
```

---

## Mobile App

The `mobile/` directory is a standalone Expo project.

### Setup

```bash
cd mobile
npm install
```

### Running

```bash
# Start Expo dev server
npm start

# Run on Android emulator / device
npm run android

# Run on iOS simulator / device (macOS only)
npm run ios
```

### Architecture

| Layer | Detail |
|-------|--------|
| Auth | JWT tokens stored in `expo-secure-store` (hardware-backed secure storage) |
| Data fetching | TanStack React Query with 2-minute stale time and 1 retry |
| Navigation | Bottom tab navigator — Dashboard, Transactions, Advisor, Rates |
| Push notifications | Expo Push Token registered at login; server sends via Expo Push API |
| API base URL | Configured in `src/api/client.ts` — point to your Django server IP |

### Building for production

```bash
# EAS Build (requires Expo account)
cd mobile
npx eas build --platform android --profile production
npx eas build --platform ios --profile production
```

---

## REST API Reference

Base URL: `/api/v1/`

### Authentication

```
POST /api/v1/token/           # Obtain JWT access + refresh tokens
POST /api/v1/token/refresh/   # Refresh access token
POST /api/v1/register/        # Create new user account
```

All other endpoints require `Authorization: Bearer <access_token>`.

### Resources

```
GET/POST        /api/v1/transactions/
GET/PUT/DELETE  /api/v1/transactions/{id}/

GET/POST        /api/v1/categories/
GET/PUT/DELETE  /api/v1/categories/{id}/

GET/POST        /api/v1/accounts/
GET/PUT/DELETE  /api/v1/accounts/{id}/

GET/POST        /api/v1/budgets/
GET/PUT/DELETE  /api/v1/budgets/{id}/
```

### Functional Endpoints

```
GET  /api/v1/dashboard/summary/    # Monthly spending summary + income totals
GET  /api/v1/advisor/feed/         # Latest 10 insights with AI advice
POST /api/v1/advisor/refresh/      # Run rules now and return updated feed
GET  /api/v1/rates/                # Current precious metal rates (public — no auth required)
POST /api/v1/device-token/         # Register Expo push token for notifications
```

### Pagination

All list endpoints return paginated responses:

```json
{
  "count": 147,
  "next": "http://localhost:8000/api/v1/transactions/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

`PAGE_SIZE` is 50. Use `?page=N` to paginate.

### Rate Limiting

| Client type | Limit |
|-------------|-------|
| Unauthenticated | 20 requests/minute |
| Authenticated user | 100 requests/minute |

---

## Background Jobs

Jobs are scheduled via Celery Beat with the DatabaseScheduler (configurable via Django Admin at `/admin/django_celery_beat/`).

| Task | Schedule | Queue | Description |
|------|----------|-------|-------------|
| `advisor.tasks.run_daily_insights` | Daily 02:00 UTC | `llm` | Runs all rules for all active users; generates Ollama advice; sends push notifications for CRITICAL insights |
| `investments.tasks.sync_all_holdings` | Daily 09:30 UTC | `default` | Fetches Zerodha holdings for all connected accounts; updates `PortfolioSnapshot` |
| `rates.tasks.refresh_metal_rates` | Every 30 minutes | `default` | Fetches Gold, Silver, Platinum prices from GoldAPI.io |
| `advisor.tasks.purge_old_insights` | Daily 03:00 UTC | `default` | Deletes `Insight` rows older than 90 days |
| `advisor.tasks.detect_recurring_for_all_users` | Daily 04:00 UTC | `default` | Flags transactions as recurring based on 3-month consecutive appearance |

### Two-queue architecture

The LLM worker (`celery_llm`) runs with `concurrency=1` to prevent saturating Ollama.
All other tasks run on the `default` worker with `concurrency=4`.

---

## Docker Deployment

The `docker-compose.yml` defines 7 services:

```bash
# Start everything
docker-compose up -d

# View logs
docker-compose logs -f web

# Run one-off management command
docker-compose exec web python manage.py createsuperuser

# Rebuild after code changes
docker-compose up -d --build web celery_default celery_llm celery_beat
```

| Service | Image | Description |
|---------|-------|-------------|
| `db` | `postgres:16` | Primary database, port 5433 → 5432 |
| `redis` | `redis:7-alpine` | Broker + cache |
| `ollama` | `ollama/ollama:latest` | LLM inference server, port 11434 |
| `web` | Built from `Dockerfile` | Gunicorn (4 workers), port 8000 |
| `celery_default` | Built from `Dockerfile` | Default queue worker, concurrency 4 |
| `celery_llm` | Built from `Dockerfile` | LLM queue worker, concurrency 1 |
| `celery_beat` | Built from `Dockerfile` | Periodic task scheduler |

> **GPU acceleration (Ollama on Linux/WSL2):** Uncomment the `deploy.resources.reservations` section in `docker-compose.yml` for Nvidia GPU passthrough.

### First-run (after `docker-compose up -d`)

The `entrypoint.sh` automatically runs `manage.py migrate` and `manage.py collectstatic`
before Gunicorn starts. No manual migration step needed on deploy.

Pull the Ollama model inside the container:

```bash
docker-compose exec ollama ollama pull qwen3:14b
```

---

## Security Considerations

| Control | Implementation |
|---------|---------------|
| Secret management | All secrets in `.env`, never hardcoded; `.env` in `.gitignore` |
| HTTPS enforcement | `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` when `DEBUG=False` |
| HSTS | `SECURE_HSTS_SECONDS = 31536000` (1 year) |
| Brute-force | `django-axes`: 5 failed attempts → 1-hour lockout, reset on success |
| Two-factor auth | TOTP device required before connecting broker accounts (`@otp_required`) |
| Field encryption | `EncryptedTextField` uses Fernet symmetric encryption for broker tokens and bank consent metadata |
| Webhook integrity | Setu consent webhooks verified with HMAC-SHA256 using `SETU_WEBHOOK_SECRET` |
| JWT hygiene | Short-lived access tokens (1h), rotating refresh tokens (14d) |
| API throttling | Anonymous: 20/min — Authenticated: 100/min |
| DB connections | `CONN_MAX_AGE = 60` — persistent connections per Gunicorn worker |

---

## Contributing

1. **Fork** the repository and create a feature branch from `main`
2. **Install** dependencies and run the test suite — all 106 tests must pass
3. **Write tests** for any new business logic — target ≥80% coverage on new modules
4. **Follow** the existing patterns:
   - HTMX partials return rendered HTML fragments, not redirects
   - Business logic lives in `services.py` or domain modules, not views
   - Use `categorization.py` as the single source of truth for categorisation — never duplicate the logic
   - Celery tasks use `acks_late=True, retry_backoff=True, max_retries=3` for idempotency
   - All secrets read from `settings` → `.env`, never hardcoded
5. **Open a pull request** with a clear description of what changed and why

---

*Built with Django 5.1 · PostgreSQL 16 · Redis 7 · Celery 5 · Ollama · React Native / Expo*
