# Sprint 6 — Dashboard & Spending Visualization

**Duration: 2 days.**

## Objective
The landing page: this month's total spend and a category breakdown chart, backed by a cached aggregation query. This sprint also establishes the **services-layer pattern** every later view-building sprint follows: business logic lives in a plain `services.py` function, the view is a thin wrapper that calls it and renders/serializes the result. This is what lets Sprint 19's mobile API reuse this exact logic later without reimplementing it.

## Preconditions
Sprint 3 (models) and Sprint 5 (base template) complete.

## Firm Decisions
- Aggregation logic lives in `dashboard/services.py: get_monthly_summary(user, year, month)` — never inline in the view. Every sprint from here on follows this same split.
- Caching: `django-redis`, key format `f"dashboard:{user.id}:{year}-{month}"`, **TTL 300 seconds**, explicit invalidation on write (not TTL-only) — the invalidation call is added in Sprint 7 when the transaction-create view exists; flagged here as a cross-sprint obligation so it isn't forgotten.
- Chart: Chart.js doughnut chart, category totals for the current calendar month only (no date-range picker in v1).
- This sprint does **not** wire in the budget-progress or advisor-feed partials — those `{% url %}` names don't exist until Sprints 9 and 12, and referencing a nonexistent URL name in a template raises `NoReverseMatch` and breaks the whole page. Each of those sprints adds its own section to `dashboard.html` when it's actually ready, not before.

## Files
- `dashboard/services.py`
- `dashboard/views.py`
- `dashboard/urls.py`
- `templates/dashboard/dashboard.html`
- `config/settings.py` (edit: add `CACHES`)
- `config/urls.py` (edit: replace the empty placeholder `dashboard.urls` include from Sprint 2 with the real one — no change needed if it already points at `dashboard.urls`, just confirm)
- `dashboard/tests/test_services.py`
- `dashboard/tests/test_views.py`

## Classes & Functions
`dashboard/services.py`:
```python
from django.db.models import Sum
from transactions.models import Transaction

def get_monthly_summary(user, year, month):
    qs = Transaction.objects.filter(user=user, date__year=year, date__month=month)
    total = qs.aggregate(total=Sum("amount"))["total"] or 0
    by_category = list(qs.values("category__name").annotate(total=Sum("amount")).order_by("-total"))
    return {"total_spent": total, "by_category": by_category}
```

`dashboard/views.py`:
```python
import json
from datetime import date
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import render
from .services import get_monthly_summary

@login_required
def dashboard(request):
    today = date.today()
    cache_key = f"dashboard:{request.user.id}:{today.year}-{today.month}"
    summary = cache.get(cache_key)
    if summary is None:
        summary = get_monthly_summary(request.user, today.year, today.month)
        cache.set(cache_key, summary, timeout=300)
    chart_labels = [row["category__name"] or "Uncategorized" for row in summary["by_category"]]
    chart_values = [float(row["total"]) for row in summary["by_category"]]
    return render(request, "dashboard/dashboard.html", {
        "total_spent": summary["total_spent"],
        "chart_labels": json.dumps(chart_labels),
        "chart_values": json.dumps(chart_values),
    })
```

## Task Breakdown
1. `pip install django-redis pytest-mock`, add both to `requirements.txt`
2. `config/settings.py` — add:
   ```python
   CACHES = {"default": {"BACKEND": "django_redis.cache.RedisCache", "LOCATION": env("CACHE_URL"),
              "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"}}}
   ```
3. Write `dashboard/services.py` — `get_monthly_summary`
4. Write `dashboard/views.py` — `dashboard` view exactly as above
5. Write `dashboard/urls.py` — `path("", views.dashboard, name="dashboard")`
6. Confirm `config/urls.py` includes `dashboard.urls` at the root path
7. Write `templates/dashboard/dashboard.html` — extends `base.html`; a summary card showing `₹{{ total_spent }}`; a `<canvas id="categoryChart">` with inline `<script>` initializing a Chart.js doughnut chart from `chart_labels`/`chart_values`
8. Write `dashboard/tests/test_services.py` and `test_views.py`

## Testing Plan
`dashboard/tests/test_services.py`:
- `test_get_monthly_summary_totals_correctly` — create 3 transactions (via `TransactionFactory`) across 2 categories, all dated this month, assert `total_spent` equals the sum and `by_category` groups correctly
- `test_get_monthly_summary_excludes_other_months` — create one transaction dated last month, assert it's excluded from the current-month summary
- `test_get_monthly_summary_no_transactions_returns_zero` — no transactions for the user, assert `total_spent == 0` and `by_category == []`

`dashboard/tests/test_views.py`:
- `test_dashboard_requires_login` — anonymous GET redirects to `login`
- `test_dashboard_renders_summary` — logged-in user with seeded transactions, GET `dashboard`, assert `total_spent` appears in the rendered response
- `test_dashboard_caches_result` — using `pytest-mock`'s `mocker.patch`, spy on `dashboard.views.get_monthly_summary`; issue two consecutive GETs within the same test; assert the spy was called **exactly once** (the second request must be served from cache)

## Load & Scale
- Cache key format and 300s TTL are fixed as stated above — this is the pattern Sprint 9 (budget progress) reuses for its own cache key.
- `values().annotate()` produces a single grouped SQL query, no per-category Python-side aggregation and no N+1 risk.
- **Cross-sprint obligation, enforced in Sprint 7**: any view that creates, edits, or deletes a `Transaction` must call `cache.delete(f"dashboard:{user.id}:{txn.date.year}-{txn.date.month}")` for the affected month — otherwise the dashboard silently serves stale totals for up to 5 minutes after every edit.

## Definition of Done
- All 6 tests pass
- `/` shows the correct total and a rendering doughnut chart for the seeded data from Sprint 3/4
- A second page load within 5 minutes does not re-run the aggregation query (verified by the caching test)
