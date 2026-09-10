# Sprint 1 — Environment & Project Setup

**Duration: 1 day.**

## Objective
Stand up the project skeleton, dependency set, and configuration that every later sprint builds on top of. Nothing else can start until this exists.

## Preconditions
None — this is the first sprint.

## Firm Decisions
- Python 3.12, Django 5.x, PostgreSQL 15+ (never SQLite, including in dev — constraint/JSONField behavior must match production from day one)
- Dependency management: `pip` + `requirements.txt`, no Poetry/PDM — keeps the deployment story (Sprint 17) simple
- Config: environment variables read via `python-decouple`, one `.env` file, never committed
- Seven Django apps created now even though most are near-empty: `accounts`, `transactions`, `budgets`, `advisor`, `integrations`, `investments`, `dashboard`. `api` and `rates` are added later (Sprints 19 and 18 respectively) — not created now, to avoid empty apps sitting unused for 15+ sprints.

## Files
- `requirements.txt`
- `.env`, `.env.example` (the latter committed, with placeholder values, so a new developer knows what to fill in)
- `.gitignore`
- `config/settings.py`, `config/urls.py` (created by `django-admin startproject`, then edited)
- `manage.py` (generated, untouched)

## Classes & Functions
None — this sprint is configuration only, no application code.

## Task Breakdown
1. `python3 -m venv venv && source venv/bin/activate`
2. `pip install django psycopg2-binary python-decouple django-htmx celery redis django-cryptography requests pandas pytest pytest-django factory_boy pytest-cov responses freezegun` — note pytest/testing packages are installed now even though the first tests aren't written until Sprint 2, so the tooling is never missing when a sprint needs it
3. `pip freeze > requirements.txt`
4. `django-admin startproject config .`
5. `python manage.py startapp accounts && python manage.py startapp transactions && python manage.py startapp budgets && python manage.py startapp advisor && python manage.py startapp integrations && python manage.py startapp investments && python manage.py startapp dashboard`
6. Create local Postgres database and role: `createdb spendtracker && createuser spendtracker`
7. Write `.env` with: `SECRET_KEY`, `DEBUG=True`, `DB_NAME=spendtracker`, `DB_USER=spendtracker`, `DB_PASSWORD`, `DB_HOST=localhost`, `DB_PORT=5432`, `REDIS_URL=redis://localhost:6379/0`, `CACHE_URL=redis://localhost:6379/1`, `OLLAMA_HOST=http://localhost:11434`, `FIELD_ENCRYPTION_KEY` (generate via `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
8. Write `.env.example` — same keys, placeholder/empty values
9. Edit `config/settings.py`: read all of the above via `decouple.config`, set `INSTALLED_APPS` (add `django_htmx` + the 7 apps), `MIDDLEWARE` (add `django_htmx.middleware.HtmxMiddleware`), `DATABASES` pointing at Postgres, `AUTH_USER_MODEL = "accounts.User"` (this line must exist before step 10 — see Sprint 2), `LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL`
10. Add `pytest.ini` at project root:
    ```ini
    [pytest]
    DJANGO_SETTINGS_MODULE = config.settings
    python_files = tests.py test_*.py *_tests.py
    ```
11. `.gitignore`: `.env`, `venv/`, `__pycache__/`, `*.pyc`, `.foglamp/` (or equivalent for any future local-secret dirs), `staticfiles/`, `node_modules/`

## Testing Plan
No application tests this sprint. Verification step instead: `python manage.py check` must exit 0 with `DEBUG=True` and a running Postgres — this is the smoke test.

## Load & Scale
Not applicable yet — no request-handling code exists. One forward-looking decision locked in now: `DATABASES["default"]["CONN_MAX_AGE"] = 60` in `settings.py`, enabling persistent connections from day one rather than retrofitting it later under load in Sprint 17.

## Definition of Done
- `python manage.py check` passes
- `python manage.py runserver` starts with no errors (even though there's nothing to see at `/` yet)
- `requirements.txt`, `.env.example`, and `.gitignore` are committed; `.env` is not
