# Sprint 9 — Budget Tracking UI

**Duration: 2 days.**

## Objective
Budget-vs-actual progress bars, computed via a cached service function and wired into the dashboard built in Sprint 6.

## Preconditions
Sprints 4 and 8 complete.

## Firm Decisions
- Same services-layer pattern as Sprint 6: `budgets/services.py: get_budget_progress(user, year, month)`, view is a thin wrapper.
- Same caching pattern as Sprint 6: key `f"budget_progress:{user.id}:{year}-{month}"`, TTL 300s.
- **Both** the dashboard cache key (Sprint 6) and this budget-progress cache key must be invalidated by any write that changes a transaction's `category` or `amount` — this includes `transaction_create` (Sprint 7) *and* `transaction_recategorize` (Sprint 8), since changing a transaction's category moves it in or out of a budget's spend total. Both existing views are edited in this sprint to add the second `cache.delete()` call.
- Progress bar visual states, fixed: `pct = min(int(spent/limit*100), 100)`; bar color is indigo under budget, red at/over budget — no intermediate "warning" (e.g. yellow at 80%) state in v1.

## Files
- `budgets/services.py`
- `budgets/views.py`
- `budgets/urls.py`
- `templates/partials/_budget_progress.html`
- `templates/dashboard/dashboard.html` (edit: add the budget-progress `hx-get` section — this is the first sprint able to safely add it, since `budgets:progress_partial` now exists)
- `transactions/views.py` (edit: second `cache.delete()` call in `transaction_create` and `transaction_recategorize`)
- `budgets/tests/test_services.py`
- `budgets/tests/test_views.py`
- `transactions/tests/test_views.py` (edit: add invalidation tests)

## Classes & Functions
`budgets/services.py`:
```python
from django.db.models import Sum
from .models import Budget
from transactions.models import Transaction

def get_budget_progress(user, year, month):
    rows = []
    for budget in Budget.objects.filter(user=user).select_related("category"):
        spent = Transaction.objects.filter(
            user=user, category=budget.category, date__year=year, date__month=month
        ).aggregate(total=Sum("amount"))["total"] or 0
        rows.append({
            "budget": budget,
            "spent": spent,
            "pct": min(int((spent / budget.monthly_limit) * 100), 100) if budget.monthly_limit else 0,
            "over": spent > budget.monthly_limit,
        })
    return rows
```

`budgets/views.py`:
```python
from datetime import date
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import render
from .services import get_budget_progress

@login_required
def progress_partial(request):
    today = date.today()
    cache_key = f"budget_progress:{request.user.id}:{today.year}-{today.month}"
    rows = cache.get(cache_key)
    if rows is None:
        rows = get_budget_progress(request.user, today.year, today.month)
        cache.set(cache_key, rows, timeout=300)
    return render(request, "partials/_budget_progress.html", {"rows": rows})
```

## Task Breakdown
1. Write `budgets/services.py` and `budgets/views.py` exactly as above
2. Write `budgets/urls.py` — `app_name = "budgets"`, `path("progress/", views.progress_partial, name="progress_partial")`
3. Confirm `config/urls.py` includes `budgets.urls`
4. Write `templates/partials/_budget_progress.html` — for each row: category name, `₹{{ row.spent }} / ₹{{ row.budget.monthly_limit }}`, and a bar `<div class="w-full bg-slate-200 rounded-full h-2"><div class="h-2 rounded-full transition-all duration-500 {% if row.over %}bg-red-500{% else %}bg-indigo-500{% endif %}" style="width: {{ row.pct }}%"></div></div>`
5. Edit `templates/dashboard/dashboard.html`: add `<div hx-get="{% url 'budgets:progress_partial' %}" hx-trigger="load, transactionsChanged from:body"></div>`
6. Edit `transactions/views.py`: in both `transaction_create` and `transaction_recategorize`, add `cache.delete(f"budget_progress:{request.user.id}:{txn.date.year}-{txn.date.month}")` immediately after the existing dashboard cache invalidation
7. Write `budgets/tests/test_services.py` and `test_views.py`
8. Extend `transactions/tests/test_views.py`

## Testing Plan
`budgets/tests/test_services.py`:
- `test_get_budget_progress_computes_spent_and_percent` — budget limit ₹1000, transactions summing ₹600 this month in that category, assert `spent == 600`, `pct == 60`, `over is False`
- `test_get_budget_progress_flags_over_budget` — spend ₹1200 against a ₹1000 limit, assert `over is True` and `pct` is capped at `100` (not `120`)
- `test_get_budget_progress_excludes_other_months` — a transaction dated last month must not count toward this month's `spent`

`budgets/tests/test_views.py`:
- `test_progress_partial_requires_login`
- `test_progress_partial_caches_result` — same `mocker.patch` spy pattern as Sprint 6, assert `get_budget_progress` is called once across two requests

`transactions/tests/test_views.py` additions:
- `test_transaction_create_invalidates_budget_progress_cache`
- `test_recategorize_invalidates_both_dashboard_and_budget_caches` — pre-populate both cache keys, POST a recategorize request that moves a transaction between two budgeted categories, assert both keys are `None` afterward

## Load & Scale
- `get_budget_progress` issues one aggregate query per budget (not a single grouped query across all budgets at once) — a deliberate simplicity choice given typical budget counts stay under 20; revisit only if that assumption stops holding, not preemptively optimized here.
- This sprint doubles the cache-invalidation surface established in Sprint 6 — flagged explicitly because Sprint 14 (bank/CSV import) creates transactions through a different code path and must invalidate both keys too; noted again in that sprint's file so it isn't missed.

## Definition of Done
- All tests pass, including the extended `transactions` suite
- In the browser: the dashboard shows budget bars matching the seeded budgets from Sprint 4; a bar turns red when spend exceeds its limit; adding or recategorizing a transaction updates the bars live with no page reload
