# Sprint 14 — Open Banking Integration

**Duration: 5 days** (14a CSV import: 2 days · 14b Account Aggregator: 3 days).

## Objective
Real transaction data instead of manual-only entry, via two sub-phases built and shipped in order: CSV/statement import first (no licensing overhead, immediate value), then RBI Account Aggregator (AA) integration for direct bank consent-based sync.

## Preconditions
- **14a (CSV import):** Sprints 7 and 13 complete.
- **14b (Account Aggregator):** additionally requires **Sprint 16 (Security Hardening)** complete — 14b stores real consent metadata and must never do so unencrypted. If working in strict file-number order, stop after 14a, complete Sprint 16, then return to 14b.

## Firm Decisions
- **CSV schema is fixed for v1**: columns `Date`, `Amount`, `Narration`, `Reference No`. Adapting to a specific bank's raw export format (column-mapping UI, format auto-detection) is explicitly **out of scope** — users reformat their statement to this schema before upload. This is a deliberate scope cut, not an oversight.
- Row-level import uses `Transaction.objects.get_or_create(...)` in a loop, **not** `Transaction.objects.bulk_create(...)`. **This refines the forward-looking note made in Sprint 3**: `bulk_create` was floated there as the general dedupe-safe batch-insert pattern, but both CSV and AA imports need `categorize()` called on each individually-created row, which `bulk_create` cannot support (it doesn't call `.save()` or return which rows were actually new when `ignore_conflicts=True` is used). `get_or_create` against the `(account, external_id)` unique constraint achieves the same dedupe safety via a lookup-then-create rather than an insert-then-catch, at a per-row cost that's entirely acceptable for a personal statement's typical row count (dozens to low hundreds).
- Cache invalidation after import targets **every distinct `(year, month)` actually touched** by newly created rows — not just the current month. A statement can span past months; invalidating only "today's month" would leave the dashboard silently stale for any historical data just imported.
- AA provider, fixed: **Setu**'s Account Aggregator sandbox. Not "Setu or Finvu or Anumati" — one concrete choice, made now, to avoid an abstraction layer built for providers this project doesn't actually integrate.
- **Exact AA endpoint paths and payload schemas are not hardcoded here** — this is not a guess left unresolved, it's an explicit statement that provider API surfaces are versioned and can change between when this plan is written and when it's implemented; the architecture (where consent state lives, how dedupe works, where the webhook lands) is fixed regardless of Setu's exact current endpoint names, which must be confirmed against Setu's live developer docs at implementation time.
- Production FIU registration is **not** pursued in this sprint — sandbox-only, matching the master architecture doc's scoping decision.

## Files (14a)
- `transactions/importers.py`
- `transactions/views.py` (edit: add `import_csv_view`)
- `transactions/urls.py` (edit: add the route)
- `templates/transactions/import_csv.html`
- `transactions/tests/test_importers.py`

## Files (14b)
- `integrations/aa_client.py`
- `integrations/views.py`
- `integrations/urls.py`
- `config/urls.py` (edit: include `integrations.urls`)
- `templates/integrations/consent_start.html`
- `integrations/tests/test_views.py`

## Classes & Functions (14a)
`transactions/importers.py`:
```python
import pandas as pd
from .models import Transaction, FinancialAccount
from .categorization import categorize

def import_csv(user, account: FinancialAccount, file):
    df = pd.read_csv(file)
    created_count = 0
    affected_months = set()
    for _, row in df.iterrows():
        txn, created = Transaction.objects.get_or_create(
            account=account,
            external_id=str(row.get("Reference No", row.name)),
            defaults={
                "user": user,
                "amount": abs(row["Amount"]),
                "date": pd.to_datetime(row["Date"]).date(),
                "merchant": str(row.get("Narration", ""))[:200],
                "source": Transaction.BANK_SYNC,
            },
        )
        if created:
            created_count += 1
            affected_months.add((txn.date.year, txn.date.month))
            if txn.category is None:
                categorize(txn)
    return created_count, affected_months
```

`transactions/views.py` addition:
```python
from django.contrib import messages
from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect
from .importers import import_csv
from .models import FinancialAccount

@login_required
def import_csv_view(request):
    if request.method == "POST":
        account = get_object_or_404(FinancialAccount, pk=request.POST["account"], user=request.user)
        count, months = import_csv(request.user, account, request.FILES["file"])
        for year, month in months:
            cache.delete(f"dashboard:{request.user.id}:{year}-{month}")
            cache.delete(f"budget_progress:{request.user.id}:{year}-{month}")
        messages.success(request, f"Imported {count} new transactions.")
        return redirect("transactions:list")
    return render(request, "transactions/import_csv.html",
                  {"accounts": FinancialAccount.objects.filter(user=request.user)})
```

## Task Breakdown (14a)
1. `pip install pandas` (already in Sprint 1's package list — confirm)
2. Write `transactions/importers.py` exactly as above
3. Edit `transactions/views.py` and `transactions/urls.py` (`path("import/", views.import_csv_view, name="import_csv")`)
4. Write `templates/transactions/import_csv.html` — account `<select>`, file input, submit (plain form POST, not HTMX — a file upload with a redirect-on-success is simpler as a full page action than a partial swap)
5. Write `transactions/tests/test_importers.py`

## Testing Plan (14a)
`transactions/tests/test_importers.py` — build CSV fixtures in-memory via `io.StringIO`, never a real file on disk:
- `test_import_csv_creates_and_categorizes_transactions` — a 3-row CSV including a merchant string that matches a Sprint 8 keyword rule (e.g. `"SWIGGY Koramangala"`), assert 3 transactions created and the matching row is auto-categorized as `Food & Dining` (deliberately avoids needing an Ollama mock by using a Tier-2-matching merchant)
- `test_import_csv_is_idempotent_on_rerun` — call `import_csv` twice with the identical CSV content, assert `Transaction.objects.count()` is unchanged after the second call
- `test_import_csv_falls_back_to_row_index_when_reference_no_missing` — CSV with no `Reference No` column, assert import still succeeds using the pandas row index as the dedupe key, with no exception raised
- `test_import_csv_returns_all_affected_months` — a CSV with rows spanning two different calendar months, assert the returned `affected_months` set has exactly 2 entries

Add to `transactions/tests/test_views.py`:
- `test_import_csv_view_requires_login`
- `test_import_csv_view_invalidates_cache_for_every_affected_month` — pre-populate dashboard/budget cache keys for two different months, POST a CSV spanning both, assert both months' keys are cleared (not just the current month's)

## Classes & Functions (14b)
`integrations/aa_client.py` — thin wrapper isolating the one part of this sprint that depends on Setu's live API surface:
```python
import requests
from django.conf import settings

class SetuAAClient:
    """Wraps Setu's Account Aggregator consent + data-fetch calls.
    Base URL, exact request/response shapes: confirm against Setu's current
    sandbox docs at implementation time — this class is the single place
    that changes if their API surface shifts, nothing else in the project
    should ever import `requests` for AA calls directly."""

    def __init__(self):
        self.base_url = settings.SETU_AA_BASE_URL
        self.client_id = settings.SETU_CLIENT_ID
        self.client_secret = settings.SETU_CLIENT_SECRET

    def create_consent_request(self, user, fi_types):
        raise NotImplementedError("Implement against Setu's current sandbox consent-request endpoint")

    def fetch_fi_data(self, consent_handle):
        raise NotImplementedError("Implement against Setu's current sandbox FI-data-fetch endpoint")
```
Shipping this as an explicit `NotImplementedError` stub rather than a guessed implementation is the firm decision here — a wrong guessed endpoint that silently fails is worse than a loud, obvious "finish this against current docs" marker.

`integrations/views.py`:
```python
from django_otp.decorators import otp_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import BankConsent
from .aa_client import SetuAAClient

@login_required
@otp_required(login_url="otp_setup")
def consent_start(request):
    return render(request, "integrations/consent_start.html")

@login_required
@otp_required(login_url="otp_setup")
def consent_initiate(request):
    client = SetuAAClient()
    result = client.create_consent_request(request.user, fi_types=["DEPOSIT"])
    BankConsent.objects.create(
        user=request.user, aa_provider="setu",
        consent_handle=result["consent_handle"], status=BankConsent.PENDING,
    )
    return redirect(result["redirect_url"])

@login_required
def consent_webhook(request):
    # Setu POSTs consent status updates here — verify signature per their
    # current docs before trusting the payload, then update BankConsent.status
    consent_handle = request.POST["consent_handle"]
    BankConsent.objects.filter(consent_handle=consent_handle).update(status=BankConsent.ACTIVE)
    return HttpResponse(status=200)
```

## Task Breakdown (14b)
1. Confirm Sprint 16 is complete (`BankConsent` model exists, encryption field available)
2. Register a Setu developer/sandbox account; get `SETU_CLIENT_ID`/`SETU_CLIENT_SECRET`/`SETU_AA_BASE_URL`; add to `.env` and `settings.py`
3. Write `integrations/aa_client.py` — `SetuAAClient` skeleton exactly as above; **fill in `create_consent_request`/`fetch_fi_data` against Setu's current sandbox docs before this sprint can actually ship** — this is the one piece of this entire 19-sprint plan that cannot be fully specified without live provider docs in hand
4. Write `integrations/views.py`, `integrations/urls.py` — `consent/` (`consent_start`), `consent/initiate/` (`consent_initiate`), `consent/webhook/` (`consent_webhook`, CSRF-exempt since it's called by Setu's servers, not a browser — add `@csrf_exempt` and verify the payload signature per Setu's docs instead)
5. Edit `config/urls.py`: `path("integrations/", include("integrations.urls"))`
6. `templates/integrations/consent_start.html` — explains what's about to happen, a "Connect my bank" button posting to `consent_initiate`
7. Write `integrations/tests/test_views.py`, mocking `SetuAAClient` entirely (never hitting a real endpoint, since the client's internals are provider-docs-dependent and not yet finalized)

## Testing Plan (14b)
`integrations/tests/test_views.py`:
- `test_consent_start_requires_otp` — a logged-in user with no confirmed TOTP device is redirected to `otp_setup` when visiting `consent_start` — proves the Sprint 16 `@otp_required` scoping is actually wired to this view
- `test_consent_initiate_creates_pending_consent` — mock `SetuAAClient.create_consent_request` (via `mocker.patch.object`) to return a fixed handle/URL, POST to `consent_initiate`, assert a `BankConsent` row is created with `status=PENDING` and the response redirects to the mocked `redirect_url`
- `test_webhook_activates_pending_consent` — create a `PENDING` `BankConsent`, POST the matching `consent_handle` to the webhook URL, assert its status becomes `ACTIVE`

## Load & Scale
- CSV import's row-by-row `get_or_create` is intentionally not batch-optimized — see the Firm Decisions section for why correctness (per-row categorization) outweighs raw insert throughput at this data scale.
- The cache-invalidation-per-affected-month fix in 14a is the concrete enforcement of the standing rule flagged back in Sprint 9: any code path that creates/moves transactions across categories or months must invalidate both cache keys for every month it touches, not just "today."
- 14b's webhook endpoint should be idempotent (repeated identical webhook deliveries — common with most webhook providers' at-least-once delivery guarantees — must not cause errors): the `.update()` call in `consent_webhook` is naturally idempotent (setting the same status twice is a no-op), so no extra dedupe logic is needed there.

## Definition of Done
- 14a: all import tests pass; uploading a real (reformatted) bank statement CSV in the browser creates transactions, auto-categorizes the recognizable ones, and the dashboard/budget views reflect the correct months immediately
- 14b: all mocked tests pass; `SetuAAClient`'s two methods are implemented against Setu's actual current sandbox docs (not left as `NotImplementedError`) before this half is considered shippable; a real sandbox consent flow can be completed end-to-end manually
