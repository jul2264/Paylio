# Sprint 5 — Frontend Foundation

**Duration: 1 day.**

## Objective
The one base template and asset pipeline every later page extends. Built once here so no later sprint touches frontend tooling again.

## Preconditions
Sprint 2 complete (nav needs working `login`/`logout`/`signup` URL names to link to).

## Firm Decisions
- Tailwind CSS via the **CLI build**, not the Play CDN — the CDN ships the whole framework uncompiled to the browser; unacceptable for anything beyond a throwaway prototype.
- HTMX and Alpine.js loaded via CDN `<script>` tags, **pinned to exact versions** (`htmx.org@1.9.12`, `alpinejs@3.x.x` — lock the resolved patch version the first time this is built and hardcode it, don't leave `@3.x.x` floating in the committed file). Self-hosting these files (serving them from Django's own static files instead of a CDN) is deferred to Sprint 17 as a production-hardening step — not needed for local development.
- Chart.js loaded the same way, pinned to `chart.js@4`.
- One `base.html`, one `_nav.html`. No per-app base template variants.

## Files
- `package.json`, `tailwind.config.js`
- `static/src/input.css`
- `static/css/main.css` (generated — gitignored, rebuilt at deploy time in Sprint 17)
- `templates/base.html`
- `templates/partials/_nav.html`
- `config/settings.py` (edit: `STATICFILES_DIRS`)
- `templates/accounts/login.html`, `signup.html` (edit: extend `base.html` instead of the bare forms from Sprint 2)

## Classes & Functions
None — this sprint is templates and build tooling only.

## Task Breakdown
1. `npm install -D tailwindcss`
2. `npx tailwindcss init`
3. `tailwind.config.js` — `content: ["./templates/**/*.html"]`
4. `static/src/input.css` — the three `@tailwind` directives (base, components, utilities)
5. `config/settings.py` — add `STATICFILES_DIRS = [BASE_DIR / "static"]`
6. Build once for local dev: `npx tailwindcss -i ./static/src/input.css -o ./static/css/main.css --watch` (left running in a terminal during development)
7. `templates/base.html` — `<head>` with the pinned CDN script tags plus `{% load static %}` / `main.css` link; `<body>` includes `partials/_nav.html`, renders Django messages, then `{% block content %}`
8. `templates/partials/_nav.html` — app name/logo, and conditionally: `{% if request.user.is_authenticated %}` show a logout link and the username, `{% else %}` show login/signup links
9. Update `templates/accounts/login.html` and `signup.html` to `{% extends "base.html" %}` with Tailwind form classes, replacing the bare `{{ form.as_p }}` from Sprint 2
10. `.gitignore`: add `static/css/main.css` and `node_modules/`

## Testing Plan
`transactions` and `accounts` apps don't get new tests this sprint (no new views or models) — instead, one template-smoke test added to `accounts/tests/test_views.py`:
- `test_login_page_includes_frontend_assets` — GET the `login` URL, assert the response contains the literal string `"htmx.org@1.9.12"` and `"chart.js@4"` — a cheap regression check that the base template's CDN includes haven't been accidentally removed by a later template edit

## Load & Scale
- Note for Sprint 17: CDN dependency is a single point of external failure — if `unpkg.com` or the Chart.js CDN is down, the whole UI's interactivity breaks even though the Django app itself is healthy. Decided now, executed then: self-host `htmx.min.js`, `alpine.min.js`, `chart.min.js` from `static/vendor/` in production, switching the `<script src>` paths in `base.html` from CDN URLs to `{% static 'vendor/...' %}` as part of the Sprint 17 deployment work.

## Definition of Done
- `npx tailwindcss ... --watch` produces `static/css/main.css` with no errors
- The login page renders with visible Tailwind styling, not raw unstyled HTML
- The new template-smoke test passes
