# Sprint 17 — Deployment

**Duration: 3 days.**

## Objective
Run the whole stack — Django, Postgres, Redis, two Celery worker types, Celery Beat, Ollama — together via Docker Compose, with production-appropriate static file serving.

## Preconditions
Sprints 1–13 complete at minimum (a fully working backend). Sprint 16 should also be done given real credentials will exist by the time this is live.

## Firm Decisions
- App server: **Gunicorn**, not uWSGI.
- Static files: **WhiteNoise**, not a separate nginx static layer — simpler operationally at this project's scale, sufficient given WhiteNoise serves pre-compressed assets with far-future cache headers directly from the Django process.
- **CDN dependency for HTMX/Alpine/Chart.js is removed entirely in this sprint**, not just for production: the vendored copies in `static/vendor/` are used unconditionally, in development and production alike, replacing Sprint 5's CDN `<script>` tags — one code path, no dev/prod branching in `base.html` to maintain.
- Migrations and `collectstatic` run automatically on container start via an entrypoint script — never a manual step an operator has to remember.
- Two separate Celery worker **services** in `docker-compose.yml`, one per queue (`celery_default`, `celery_llm`) — the deployment-level realization of Sprint 13's queue-routing decision. `celery_default` can be horizontally scaled independently (`docker compose up --scale celery_default=3`); `celery_llm` must never be scaled past 1 replica, since doing so would defeat the entire point of the single-concurrency GPU-protecting queue.
- Ollama runs as its own containerized service with a persistent named volume for model weights, with GPU passthrough configured for an Nvidia host — explicitly documented as removable for a CPU-only host.

## Files
- `Dockerfile`
- `docker-compose.yml`
- `entrypoint.sh`
- `config/settings.py` (edit: WhiteNoise middleware, `STATIC_ROOT`, `STATICFILES_STORAGE`, `ALLOWED_HOSTS` from env)
- `static/vendor/htmx.min.js`, `static/vendor/alpine.min.js`, `static/vendor/chart.min.js` (downloaded, committed)
- `templates/base.html` (edit: swap CDN `<script src>` for `{% static 'vendor/...' %}`)

## Classes & Functions
Not applicable — this sprint is infrastructure configuration, not application code.

## Task Breakdown
1. `pip install gunicorn whitenoise`, add to `requirements.txt`
2. `config/settings.py`:
   ```python
   MIDDLEWARE.insert(MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,
                      "whitenoise.middleware.WhiteNoiseMiddleware")
   STATIC_ROOT = BASE_DIR / "staticfiles"
   STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
   ALLOWED_HOSTS = env("ALLOWED_HOSTS", cast=lambda v: [s.strip() for s in v.split(",")])
   ```
3. Download the pinned versions from Sprint 5 (`htmx.org@1.9.12`, the resolved Alpine 3.x patch version, `chart.js@4`) into `static/vendor/`, commit them
4. Edit `templates/base.html`: replace the three CDN `<script src>` tags with `{% static 'vendor/htmx.min.js' %}` etc.
5. Write `entrypoint.sh`:
   ```bash
   #!/bin/sh
   set -e
   python manage.py migrate --noinput
   python manage.py collectstatic --noinput
   exec "$@"
   ```
6. Write `Dockerfile`:
   ```dockerfile
   FROM python:3.12-slim
   WORKDIR /app
   RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY . .
   RUN chmod +x entrypoint.sh
   ENTRYPOINT ["./entrypoint.sh"]
   CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
   ```
7. Write `docker-compose.yml` with services `db` (postgres:16), `redis` (redis:7), `ollama` (ollama/ollama, GPU `deploy` block, persistent `ollama_models` volume), `web` (gunicorn), `celery_default` (`-Q default -c 4`), `celery_llm` (`-Q llm -c 1`), `celery_beat` — every service using `env_file: .env`

## Testing Plan
No automated test suite applies to infrastructure config directly; this sprint substitutes a **manual verification checklist**, run once against a clean checkout:
1. `docker compose up --build` — all services start with no errors
2. `docker compose exec web python manage.py createsuperuser`
3. `/admin/` login succeeds
4. `/` loads; browser devtools' Network tab confirms JS assets load from `/static/vendor/...`, not `unpkg.com` or any external CDN
5. Add a transaction — confirm the HTMX partial swap still works end-to-end in the containerized environment
6. `docker compose logs celery_default` and `docker compose logs celery_llm` — confirm each worker reports connection to its respective queue
7. `docker compose logs celery_beat` — confirm `nightly-insights` and `daily-holdings-sync` schedules are registered

## Load & Scale
- `celery_default` is designed to scale horizontally (`--scale celery_default=N`); `celery_llm` is designed to **never** scale past 1 replica — this is the single most important constraint carried from Sprint 13 into the deployment topology, and it's enforced by having them be genuinely separate Compose services rather than one service with a queue argument that someone could accidentally scale up.
- Gunicorn's `--workers 4` and `celery_default`'s `-c 4` are both tied to a 4-core assumption — revisit both together against the actual production host's core count; they were deliberately chosen to match each other, not picked independently.
- WhiteNoise is judged sufficient for this app's traffic scale; a dedicated CDN/reverse-proxy static layer is explicitly deferred as unnecessary until there's a concrete reason to add one.

## Definition of Done
- All 7 manual verification steps pass on a clean checkout
- `docker compose up --build` succeeds with no manual intervention beyond creating a superuser
