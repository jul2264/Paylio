# Sprint Plan — Overview & Global Decisions

Companion to `spending-tracker-architecture.md` (the technical reference: code, models, endpoints). This overview plus the 19 sprint files that follow it are the execution plan — one file per sprint, each self-contained enough to hand to a developer with no other context.

## Global Firm Decisions (apply to every sprint, not restated per file except where a sprint adds to them)

**Testing stack — fixed:**
- Runner: `pytest` + `pytest-django`
- Test data: `factory_boy` — every app gets `tests/factories.py`
- External HTTP mocking: `responses` library — used for Ollama, GoldAPI.io, Kite Connect, and AA calls in tests; no test ever makes a real network call
- Time-dependent tests (trend/period calculations): `freezegun`
- Coverage: `pytest-cov`, **80% minimum** on every `services.py` / business-logic module (models, services, rules, categorization, ai.py) — templates and admin registration are excluded from the target
- Standard layout per app: `tests/__init__.py`, `tests/factories.py`, `tests/test_models.py`, `tests/test_services.py` (or a task-specific name — e.g. `test_rules.py`, `test_categorization.py`), `tests/test_views.py`

**Load / performance stack — fixed:**
- Cache backend: `django-redis`, same Redis process as the Celery broker, separate logical DB (`REDIS_URL` for Celery = db 0, `CACHE_URL` = db 1)
- Pagination: DRF `PageNumberPagination`, `PAGE_SIZE = 50`, set globally via `REST_FRAMEWORK["DEFAULT_PAGINATION_CLASS"]` — every list endpoint inherits it, no per-view opt-out
- Celery queues: exactly two — `default` (everything) and `llm` (anything that calls Ollama). The `llm` queue always runs at **concurrency 1**, regardless of host core count — one GPU serves one request at a time; concurrent requests risk OOM, not speedup
- Celery task hardening, applied to every task calling an external API (Ollama, GoldAPI.io, AA, broker): `acks_late=True`, `retry_backoff=True`, `max_retries=3`
- Rate limiting: DRF `UserRateThrottle` at `100/min` on all authenticated write endpoints; `django-axes` lockout after 5 failed logins in 1 hour

**Definition of Done — every sprint, no exceptions:**
1. All tests listed in that sprint's file pass; coverage threshold met on new code
2. `python manage.py check` and `python manage.py makemigrations --check --dry-run` both exit clean
3. Manual smoke-test steps (listed per sprint) completed once against local Postgres — never validated against SQLite, since the deployed target is Postgres and behavior around constraints/JSONField differs
4. No hardcoded secrets — anything new goes in `.env` and is read via `settings.py`

## Sprint Sequence & Dependencies

| # | Sprint | Depends on | Est. days |
|---|---|---|---|
| 1 | Environment & Project Setup | — | 1 |
| 2 | Authentication & User Accounts | 1 | 1 |
| 3 | Core Domain Models | 2 | 2 |
| 4 | Budgets App | 3 | 1 |
| 5 | Frontend Foundation | 1 | 1 |
| 6 | Dashboard & Spending Visualization | 3, 5 | 2 |
| 7 | Transaction Management (CRUD + HTMX) | 3, 5, 6 | 3 |
| 8 | Expense Categorization Pipeline | 7 | 3 |
| 9 | Budget Tracking UI | 4, 8 | 2 |
| 10 | Robo-Advisor — Rule Engine | 4, 8 | 3 |
| 11 | Robo-Advisor — Local LLM Layer | 10 | 2 |
| 12 | Advisor Feed UI | 10, 11 | 2 |
| 13 | Background Jobs (Celery) | 8, 11 | 2 |
| 14 | Open Banking Integration | 7, 13 for CSV import (14a); **also 16** before building consent/token storage (14b) | 5 |
| 15 | Investment / Demat Integration | 13, 16 | 5 |
| 16 | Security Hardening | 1 | 2 |
| 17 | Deployment | 1–13 minimum | 3 |
| 18 | Live Precious Metal Rates | 5, 13 | 2 |
| 19 | Mobile Apps (React Native) | 17 (a deployed API to point at) | 8 |

**Total: 49 working days, solo developer, full-time — roughly 10 weeks.**

**Critical path** (the sequence that cannot be reordered): 1 → 2 → 3 → 5 → 6 → 7 → 8 → 10 → 11 → 12 → 13 → 16 → 14 → 15 → 17 → 19.
**Off-critical-path** (can be pulled forward, deferred, or built in parallel by a second developer without breaking anything downstream): Sprint 4 (Budgets) only needs Sprint 3; Sprint 9 only needs 4 and 8; Sprint 18 only needs 5 and 13.

**One numbering-vs-execution note, stated plainly:** the sprint files are numbered 1–19 to match the step list as given, but Sprint 16 (Security Hardening) must be *executed* before the token-storage half of Sprint 14 (Open Banking) and all of Sprint 15 (Investments) — both store real third-party credentials and must never do so unencrypted, even temporarily. Sprint 14 is split into 14a (CSV import — no token storage, safe to build in numeric order) and 14b (Account Aggregator consent flow — storage-bearing, blocked on 16). If working strictly in file-number order, build 14a on schedule and treat 14b as deferred until 16 is done, rather than building it unencrypted and retrofitting encryption after.

Each sprint file below follows the same structure: **Objective** (what/why) → **Preconditions** (when) → **Firm Decisions** (no open choices) → **Files** (exact paths) → **Classes & Functions** (signatures + responsibility) → **Task Breakdown** (ordered, checkable) → **Testing Plan** (explicit test cases) → **Load & Scale** → **Definition of Done**.
