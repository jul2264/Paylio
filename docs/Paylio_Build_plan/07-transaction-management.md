# Sprint 7 — Transaction Management (CRUD + HTMX)

**Duration: 3 days.**

## Objective
Manual transaction entry, listing, and filtering — the core daily-use loop. Category assignment is manual in this sprint (a dropdown on the form); automatic categorization is added in Sprint 8 by editing the view built here, not by this sprint itself.

## Preconditions
Sprints 3, 5, 6 complete.

## Firm Decisions
- `TransactionForm` is a plain `ModelForm` — no client-side JS validation beyond browser-default HTML5 required-field checks.
- The transaction table partial shows the **100 most recent** transactions with no further pagination UI in v1 (`qs[:100]`) — a "load more" control is explicitly out of scope for v1; if this becomes a real limitation, it's revisited then, not preemptively built now.
- `transaction_table_partial` **must** use `.select_related("category", "account")` — the row template accesses both on every row, and without this the view issues 2N extra queries for N rows.
- Every write path here enforces the Sprint 6 cache-invalidation obligation: `transaction_create` deletes the dashboard cache key for the transaction's month immediately after saving.
- HTMX event contract: on successful create, the response carries an `HX-Trigger: transactionsChanged` header (via `django_htmx.http.trigger_client_event`) — this is the one and only signal other page regions listen for; no other custom event names are introduced in this sprint.

## Files
- `transactions/forms.py`
- `transactions/views.py`
- `transactions/urls.py`
- `templates/transactions/list.html`
- `templates/partials/_transaction_table.html`
- `templates/partials/_transaction_row.html`
- `templates/partials/_transaction_form_errors.html`
- `config/urls.py` (edit: confirm `transactions.urls` include is live, not the empty Sprint-2 placeholder)
- `transactions/tests/test_views.py`

## Classes & Functions
`transactions/forms.py`:
```python
from django import forms
from .models import Transaction

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["account", "category", "amount", "date", "merchant", "description"]
```

`transactions/views.py`:
```python
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import render
from django_htmx.http import trigger_client_event
from .forms import TransactionForm
from .models import Transaction

@login_required
def transaction_list(request):
    return render(request, "transactions/list.html", {"form": TransactionForm()})

@login_required
def transaction_table_partial(request):
    qs = Transaction.objects.filter(user=request.user).select_related("category", "account").order_by("-date")
    category = request.GET.get("category")
    if category:
        qs = qs.filter(category_id=category)
    return render(request, "partials/_transaction_table.html", {"transactions": qs[:100]})

@login_required
def transaction_create(request):
    form = TransactionForm(request.POST)
    form.instance.user = request.user
    if form.is_valid():
        txn = form.save()
        cache.delete(f"dashboard:{request.user.id}:{txn.date.year}-{txn.date.month}")
        response = render(request, "partials/_transaction_row.html", {"txn": txn})
        return trigger_client_event(response, "transactionsChanged")
    return render(request, "partials/_transaction_form_errors.html", {"form": form})
```

## Task Breakdown
1. Write `transactions/forms.py`
2. Write `transactions/views.py` — all three views exactly as above
3. Write `transactions/urls.py` — `app_name = "transactions"`, routes: `""` → `list`, `"table/"` → `table_partial`, `"add/"` → `create`
4. Confirm `config/urls.py` has `path("transactions/", include("transactions.urls"))`
5. `templates/transactions/list.html` — extends `base.html`; the add-transaction form (`hx-post` to `create`, `hx-target="#txn-table-body"`, `hx-swap="afterbegin"`); a category `<select>` (`hx-get` to `table_partial`, `hx-target="#txn-table-body"`); a `<table>` with `<tbody id="txn-table-body" hx-get="{% url 'transactions:table_partial' %}" hx-trigger="load">`
6. `templates/partials/_transaction_table.html` — loops `transactions`, includes `_transaction_row.html` per row
7. `templates/partials/_transaction_row.html` — one `<tr>`: date, merchant, category name (or "Uncategorized"), amount
8. `templates/partials/_transaction_form_errors.html` — re-renders the form with Django's default error rendering
9. Write `transactions/tests/test_views.py`

## Testing Plan
`transactions/tests/test_views.py`:
- `test_transaction_list_requires_login` — anonymous GET redirects to `login`
- `test_transaction_create_saves_and_returns_row` — POST valid data, assert `Transaction.objects.count() == 1` and the merchant name appears in the response body
- `test_transaction_create_invalid_returns_errors` — POST with `date` omitted, assert 200 (not a redirect), an error is present in the response, and `Transaction.objects.count() == 0`
- `test_transaction_create_invalidates_dashboard_cache` — pre-populate `cache.set(f"dashboard:{user.id}:{year}-{month}", {...}, 300)`, POST a transaction dated that same month, assert `cache.get(key) is None` afterward
- `test_transaction_create_sends_htmx_trigger_header` — POST valid data, assert `response["HX-Trigger"] == "transactionsChanged"`
- `test_transaction_table_partial_filters_by_category` — create transactions in two different categories, GET `table_partial?category=<id>`, assert only the matching category's transactions appear in the response
- `test_transaction_table_partial_caps_at_100` — bulk-create 105 transactions via the factory, GET `table_partial`, assert exactly 100 appear in `response.context["transactions"]`

## Load & Scale
- `.select_related("category", "account")` is mandatory in `transaction_table_partial` — without it, rendering 100 rows issues up to 200 extra queries. Verify with `django.test.utils.CaptureQueriesContext` in a test if query-count regressions become a concern later; not required for this sprint's test suite.
- No DRF/API throttling applies here — this is a session-authenticated, CSRF-protected HTML form, not a public API. The `UserRateThrottle` global decision applies only to the `/api/v1/` routes built in Sprint 19.
- The 100-row cap on the HTMX partial is a deliberate v1 scope cut, not a performance workaround for a real dataset size problem — a personal finance app's monthly transaction count is small; this exists to keep the initial page-load payload predictable, not because 100+ rows would be slow to query.

## Definition of Done
- All 7 tests pass
- In a real browser: adding a transaction updates the table instantly with no full page reload, and the dashboard's total (Sprint 6) reflects the new transaction on next visit
- Filtering by category updates the table without a page reload
