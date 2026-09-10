# Sprint 18 — Live Precious Metal Rates (Gold / Silver / Platinum)

**Duration: 2 days.**

## Objective
Gold (24K/22K/18K), silver (999/958/925/900/800), and platinum (999/950/900/850) rates, refreshed periodically and shown on the dashboard.

## Preconditions
Sprints 5 and 13 complete. Independent of the rest of the domain (transactions, budgets, advisor) — buildable any time after those two.

## Firm Decisions
- Data source, fixed: **GoldAPI.io**. Not "GoldAPI.io or metals-api.com" — one concrete provider, integrated now.
- Only the pure/finest rate (999 fineness / 24K) is stored per metal per snapshot — every purity variant is a computed multiplier, never separately stored.
- Refresh cadence: **every 30 minutes**, via Celery Beat, on the **`default`** queue (an external API call, but not Ollama — no GPU contention concern, so it does not belong on `llm`).
- Client-side polling: HTMX `hx-trigger="load, every 300s"` (5 minutes) on the dashboard widget — deliberately looser than the 30-minute server refresh isn't possible (300s < 1800s), so this polls more often than the data actually changes; accepted as harmless given the request is cheap (reads one small cached-in-DB row per metal, no external call on the request path).
- **Access control differs from Sprint 19's API version on purpose**: the HTML partial built in this sprint requires login (`@login_required`), consistent with every other dashboard widget in this project, even though the underlying rate data isn't user-specific. Sprint 19's `/api/v1/rates/` endpoint is intentionally `AllowAny` instead, so a logged-out mobile screen can still show live rates — that's a deliberate, documented difference between the two surfaces, not an inconsistency.

## Files
- `rates/models.py`, `rates/admin.py`, `rates/migrations/0001_initial.py` (generated)
- `rates/purity.py`
- `rates/fetcher.py`
- `rates/tasks.py`
- `rates/views.py`
- `rates/urls.py`
- `config/settings.py` (edit: `METALS_API_KEY`; add `refresh-metal-rates` to `CELERY_BEAT_SCHEDULE`)
- `config/urls.py` (edit: include `rates.urls`)
- `templates/partials/_metal_rates.html`
- `templates/dashboard/dashboard.html` (edit: add the rates widget — safe now, `rates:widget` exists)
- `rates/tests/test_purity.py`, `test_fetcher.py`, `test_tasks.py`, `test_views.py`

## Classes & Functions
`rates/models.py`:
```python
from django.db import models

class MetalRateSnapshot(models.Model):
    GOLD, SILVER, PLATINUM = "GOLD", "SILVER", "PLATINUM"
    METAL_CHOICES = [(GOLD, "Gold"), (SILVER, "Silver"), (PLATINUM, "Platinum")]

    metal = models.CharField(max_length=10, choices=METAL_CHOICES)
    price_per_gram_999 = models.DecimalField(max_digits=10, decimal_places=2)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["metal", "-fetched_at"])]
```

`rates/purity.py`:
```python
GOLD_PURITIES = {"24K": 1.0, "22K": 22/24, "18K": 18/24}
SILVER_PURITIES = {"999 Fine": 0.999, "958 Britannia": 0.958, "925 Sterling": 0.925, "900 Coin": 0.900, "800 Continental": 0.800}
PLATINUM_PURITIES = {"999": 0.999, "950": 0.950, "900": 0.900, "850": 0.850}

def compute_purity_rates(base_price_per_gram, purity_table):
    return {label: round(base_price_per_gram * factor, 2) for label, factor in purity_table.items()}
```

`rates/fetcher.py`:
```python
import requests
from django.conf import settings

TROY_OUNCE_TO_GRAM = 31.1034768
SYMBOLS = {"GOLD": "XAU", "SILVER": "XAG", "PLATINUM": "XPT"}

def fetch_price_per_gram_inr(metal: str) -> float:
    resp = requests.get(
        f"https://www.goldapi.io/api/{SYMBOLS[metal]}/INR",
        headers={"x-access-token": settings.METALS_API_KEY},
        timeout=15,
    )
    resp.raise_for_status()
    price_per_oz_inr = resp.json()["price"]
    return price_per_oz_inr / TROY_OUNCE_TO_GRAM
```

`rates/tasks.py`:
```python
from celery import shared_task
from .fetcher import fetch_price_per_gram_inr
from .models import MetalRateSnapshot

@shared_task(acks_late=True, retry_backoff=True, max_retries=3)
def refresh_metal_rates():
    for metal in ["GOLD", "SILVER", "PLATINUM"]:
        MetalRateSnapshot.objects.create(metal=metal, price_per_gram_999=fetch_price_per_gram_inr(metal))
```

`rates/views.py`:
```python
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import MetalRateSnapshot
from .purity import GOLD_PURITIES, SILVER_PURITIES, PLATINUM_PURITIES, compute_purity_rates

@login_required
def rates_widget(request):
    context = {}
    for metal, table, key in [("GOLD", GOLD_PURITIES, "gold"), ("SILVER", SILVER_PURITIES, "silver"), ("PLATINUM", PLATINUM_PURITIES, "platinum")]:
        latest = MetalRateSnapshot.objects.filter(metal=metal).order_by("-fetched_at").first()
        context[key] = compute_purity_rates(float(latest.price_per_gram_999), table) if latest else {}
    return render(request, "partials/_metal_rates.html", context)
```

## Task Breakdown
1. Register a GoldAPI.io account, get an API key, add `METALS_API_KEY` to `.env`/`settings.py`
2. Write `rates/models.py`, `rates/admin.py`; `python manage.py makemigrations rates && python manage.py migrate`
3. Write `rates/purity.py`, `rates/fetcher.py`, `rates/tasks.py`
4. Edit `config/settings.py`'s `CELERY_BEAT_SCHEDULE`:
   ```python
   CELERY_BEAT_SCHEDULE["refresh-metal-rates"] = {
       "task": "rates.tasks.refresh_metal_rates", "schedule": 60 * 30,
   }
   ```
5. Write `rates/views.py`, `rates/urls.py` (`app_name = "rates"`, `path("widget/", views.rates_widget, name="widget")`)
6. Edit `config/urls.py`: include `rates.urls`
7. Write `templates/partials/_metal_rates.html` — three cards (gold/silver/platinum), each listing its purities and computed prices
8. Edit `templates/dashboard/dashboard.html`: add `<div hx-get="{% url 'rates:widget' %}" hx-trigger="load, every 300s"></div>`
9. Write all four test files

## Testing Plan
`rates/tests/test_purity.py`:
- `test_compute_purity_rates_gold` — base ₹6000/gram, assert `24K == 6000.0`, `22K == 5500.0` (`6000 * 22/24`), `18K == 4500.0`
- `test_compute_purity_rates_silver` and `test_compute_purity_rates_platinum` — same pattern against their respective tables

`rates/tests/test_fetcher.py` (mock via `responses`, no real GoldAPI call in any test):
- `test_fetch_price_converts_oz_to_gram_correctly` — mock a `{"price": 250000}` response, assert the returned value equals `250000 / 31.1034768`
- `test_fetch_price_raises_on_http_error` — mock a 401/500 response, assert `requests.exceptions.HTTPError` is raised

`rates/tests/test_tasks.py`:
- `test_refresh_metal_rates_creates_a_snapshot_per_metal` — mock `fetch_price_per_gram_inr` for all three metals, call `refresh_metal_rates.apply()`, assert exactly 3 `MetalRateSnapshot` rows exist, one per metal

`rates/tests/test_views.py`:
- `test_rates_widget_requires_login`
- `test_rates_widget_computes_all_purities_from_latest_snapshot` — create one `MetalRateSnapshot` per metal, GET the widget, assert every purity label from all three tables appears with the correctly computed value
- `test_rates_widget_handles_no_data_without_crashing` — no snapshots exist yet, GET the widget, assert a 200 response with empty data rather than a 500

## Load & Scale
- 30-minute server-side polling is deliberately loose relative to GoldAPI's free-tier rate limits — Indian retail bullion rates update once or twice daily even on jewelers' own sites, so this cadence is genuinely "live enough" for the use case, not a compromise.
- The 5-minute client-side HTMX poll being tighter than the 30-minute server refresh is intentional and harmless — each poll only reads the latest cached `MetalRateSnapshot` rows (an indexed, trivial query), never triggers an external API call itself.

## Definition of Done
- All 7 tests pass with no real network call to GoldAPI.io
- The dashboard shows correct, live-updating purity breakdowns for all three metals once `refresh_metal_rates` has run at least once (verify manually via `python manage.py shell` → `from rates.tasks import refresh_metal_rates; refresh_metal_rates.apply()`)
