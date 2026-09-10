# Sprint 15 — Investment / Demat Integration

**Duration: 5 days.**

## Objective
Read-only equity holdings synced from a real broker account, with daily portfolio valuation snapshots.

## Preconditions
Sprints 13 and 16 complete (Celery infrastructure; `EncryptedTextField` and the encryption/2FA pattern established).

## Firm Decisions
- Broker, fixed: **Zerodha Kite Connect**. Not "Kite Connect or Upstox or Angel One" — one concrete integration, built now; others are a future addition following the identical pattern, not designed here.
- Scope, fixed: **read-only** — holdings and valuation only. Order placement is explicitly out of scope; this app's use case (portfolio visibility for the robo-advisor) never requires it, and it carries materially more regulatory/liability weight than this project takes on.
- Token storage: `BrokerConnection.encrypted_access_token` uses `integrations.fields.EncryptedTextField` from Sprint 16 — imported, never reimplemented.
- Daily token expiry (Kite tokens expire ~20 hours after login, with no silent refresh possible by design/regulation) is handled as: the sync task **skips** any connection whose token has expired rather than attempting a refresh, and the holdings view surfaces a `needs_reconnect` flag the template uses to prompt a manual re-login. No retry-around-expiry logic is built — it cannot work regardless of implementation effort.
- One `holdings()` API call per user per sync — never per-symbol — respecting Kite's rate limits by construction rather than by hardcoding a specific limit number.
- Daily sync is staggered across users via `apply_async(countdown=user_id % 300)` — spreads all users' sync calls across a 5-minute window rather than firing simultaneously.
- Sync tasks run on the **`default`** Celery queue, not `llm` — they never call Ollama and shouldn't compete for the GPU-protecting single-concurrency queue.

## Files
- `investments/models.py`
- `investments/admin.py`
- `investments/migrations/0001_initial.py` (generated)
- `investments/views.py`
- `investments/urls.py`
- `investments/tasks.py`
- `integrations/brokers/__init__.py`, `integrations/brokers/kite.py`
- `config/settings.py` (edit: `KITE_API_KEY`, `KITE_API_SECRET`; add `daily-holdings-sync` to `CELERY_BEAT_SCHEDULE`)
- `config/urls.py` (edit: include `investments.urls`)
- `templates/investments/holdings.html`
- `investments/tests/factories.py`, `test_models.py`, `test_tasks.py`, `test_views.py`
- `integrations/brokers/tests/test_kite.py`

## Classes & Functions
`investments/models.py`:
```python
from django.conf import settings
from django.db import models
from integrations.fields import EncryptedTextField

class BrokerConnection(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    broker = models.CharField(max_length=30, default="zerodha")
    encrypted_access_token = EncryptedTextField()
    token_expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

class Holding(models.Model):
    EQUITY, MUTUAL_FUND, BOND = "EQUITY", "MUTUAL_FUND", "BOND"
    ASSET_CHOICES = [(EQUITY, "Equity"), (MUTUAL_FUND, "Mutual Fund"), (BOND, "Bond")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    broker_connection = models.ForeignKey(BrokerConnection, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=50)
    asset_type = models.CharField(max_length=15, choices=ASSET_CHOICES, default=EQUITY)
    quantity = models.DecimalField(max_digits=12, decimal_places=4)
    avg_price = models.DecimalField(max_digits=12, decimal_places=2)
    last_synced_price = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    last_synced_at = models.DateTimeField(null=True)

    class Meta:
        unique_together = ("broker_connection", "symbol")

class PortfolioSnapshot(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField()
    total_value = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        unique_together = ("user", "date")
```

`integrations/brokers/kite.py`:
```python
from kiteconnect import KiteConnect
from django.conf import settings

def get_login_url():
    return KiteConnect(api_key=settings.KITE_API_KEY).login_url()

def exchange_request_token(request_token):
    kite = KiteConnect(api_key=settings.KITE_API_KEY)
    data = kite.generate_session(request_token, api_secret=settings.KITE_API_SECRET)
    return data["access_token"]

def fetch_holdings(access_token):
    kite = KiteConnect(api_key=settings.KITE_API_KEY)
    kite.set_access_token(access_token)
    return kite.holdings()
```

`investments/views.py`:
```python
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django_otp.decorators import otp_required
from integrations.brokers.kite import get_login_url, exchange_request_token
from .models import BrokerConnection

@login_required
@otp_required(login_url="otp_setup")
def connect_broker(request):
    return redirect(get_login_url())

@login_required
@otp_required(login_url="otp_setup")
def broker_callback(request):
    access_token = exchange_request_token(request.GET["request_token"])
    BrokerConnection.objects.update_or_create(
        user=request.user, broker="zerodha",
        defaults={"encrypted_access_token": access_token,
                  "token_expires_at": timezone.now() + timedelta(hours=20)},
    )
    return redirect("investments:holdings")

@login_required
def holdings_view(request):
    connection = BrokerConnection.objects.filter(user=request.user, broker="zerodha").first()
    expired = connection is None or connection.token_expires_at < timezone.now()
    holdings = [] if expired else connection.holding_set.all()
    return render(request, "investments/holdings.html", {"holdings": holdings, "needs_reconnect": expired})
```

`investments/tasks.py`:
```python
from datetime import date
from celery import shared_task
from django.utils import timezone
from integrations.brokers.kite import fetch_holdings
from .models import BrokerConnection, Holding, PortfolioSnapshot

@shared_task(acks_late=True, retry_backoff=True, max_retries=3)
def sync_holdings_for_user(user_id):
    connection = BrokerConnection.objects.filter(user_id=user_id, broker="zerodha").first()
    if connection is None or connection.token_expires_at < timezone.now():
        return
    raw_holdings = fetch_holdings(connection.encrypted_access_token)
    total_value = 0
    for h in raw_holdings:
        Holding.objects.update_or_create(
            broker_connection=connection, symbol=h["tradingsymbol"],
            defaults={"user_id": user_id, "asset_type": Holding.EQUITY,
                      "quantity": h["quantity"], "avg_price": h["average_price"],
                      "last_synced_price": h["last_price"], "last_synced_at": timezone.now()},
        )
        total_value += h["quantity"] * h["last_price"]
    PortfolioSnapshot.objects.update_or_create(
        user_id=user_id, date=date.today(), defaults={"total_value": total_value},
    )

@shared_task
def sync_all_holdings():
    for connection in BrokerConnection.objects.filter(broker="zerodha"):
        sync_holdings_for_user.apply_async(args=[connection.user_id], countdown=connection.user_id % 300)
```

## Task Breakdown
1. `pip install kiteconnect`, add to `requirements.txt`
2. Register a Kite Connect developer app; obtain `KITE_API_KEY`/`KITE_API_SECRET`; add to `.env`/`settings.py`
3. Write `investments/models.py` exactly as above; `investments/admin.py` registers all three
4. `python manage.py makemigrations investments && python manage.py migrate`
5. Write `integrations/brokers/kite.py`
6. Write `investments/views.py`, `investments/urls.py` (`app_name = "investments"`: `connect/` → `connect_broker`, `callback/` → `broker_callback`, `holdings/` → `holdings_view` named `holdings`)
7. Edit `config/urls.py`: include `investments.urls`
8. Write `investments/tasks.py`; edit `config/settings.py`'s `CELERY_BEAT_SCHEDULE` (from Sprint 13) to add:
   ```python
   CELERY_BEAT_SCHEDULE["daily-holdings-sync"] = {
       "task": "investments.tasks.sync_all_holdings", "schedule": crontab(hour=9, minute=30),
   }
   ```
9. `templates/investments/holdings.html` — holdings table, or a "Reconnect your broker" prompt when `needs_reconnect` is true
10. Write all listed test files

## Testing Plan
`investments/tests/test_models.py`:
- `test_holding_unique_per_connection_and_symbol`
- `test_portfolio_snapshot_unique_per_user_and_date`

`integrations/brokers/tests/test_kite.py` (mock the `kiteconnect.KiteConnect` class via `mocker.patch`):
- `test_get_login_url_delegates_to_kiteconnect`
- `test_exchange_request_token_returns_access_token`
- `test_fetch_holdings_returns_raw_kite_response`

`investments/tests/test_tasks.py`:
- `test_sync_holdings_creates_holdings_and_snapshot` — mock `fetch_holdings` to return a fixed 2-row list, call `sync_holdings_for_user.apply(args=[user.id])`, assert both `Holding` rows and a correct-total `PortfolioSnapshot` are created
- `test_sync_holdings_skips_expired_connection` — `token_expires_at` in the past, call the task, assert `fetch_holdings` (mocked) is **not** called and no `Holding` is created
- `test_sync_all_holdings_staggers_each_user` — mock `apply_async`, create 2 connections, call `sync_all_holdings`, assert `apply_async` was called twice with the expected `countdown` values

`investments/tests/test_views.py`:
- `test_connect_broker_requires_otp`
- `test_broker_callback_stores_encrypted_token` — mock `exchange_request_token`, GET the callback with a `request_token` param, assert a `BrokerConnection` is created and its token round-trips correctly through `EncryptedTextField` when re-fetched fresh from the DB
- `test_holdings_view_shows_reconnect_prompt_when_token_expired`

## Load & Scale
- The one-call-per-user `holdings()` pattern and the `user_id % 300` staggering are the two concrete techniques protecting Kite's API from a thundering herd — restated here because they're this sprint's primary load consideration, not an afterthought.
- `sync_holdings_for_user`/`sync_all_holdings` are explicitly confirmed to run on the `default` queue, not `llm` — no GPU contention with the advisor's Ollama calls.
- No portfolio-value caching is added in v1 — `holdings_view` reads directly from the `Holding` table, which is only ever written once daily by the sync task, so there's no meaningful read-query cost to amortize with a cache.

## Definition of Done
- All tests pass with `kiteconnect` fully mocked (no real broker account required for CI)
- With a real (or Kite's sandbox) trading account: connecting a broker and running `sync_all_holdings` populates real holdings and a portfolio snapshot; the UI clearly shows a reconnect prompt once the token has expired
