# Sprint 13 — Background Jobs (Celery)

**Duration: 2 days.**

## Objective
Stand up Celery for real, and close the one deliberate gap left open since Sprint 8: wire the Tier-3 LLM categorization fallback into `transactions/categorization.py`. Also establishes the nightly insight-generation schedule.

## Preconditions
Sprints 8 and 11 complete.

## Firm Decisions
- **Exactly two queues: `default` and `llm`.** Every task that calls Ollama — currently `run_daily_insights` and `categorize_with_llm`, and no others, ever — is routed to `llm` via `CELERY_TASK_ROUTES`, not left to land on `default` by convention. The `llm` queue's worker always runs at **concurrency 1** regardless of host core count; `default`'s worker runs at `-c 4` (revisited in Sprint 17 against the actual deploy host's core count).
- Every task calling an external API (Ollama now; GoldAPI/AA/broker from Sprints 14–15, 18 later) gets `acks_late=True, retry_backoff=True, max_retries=3` on the `@shared_task` decorator — fixed policy, not tuned per task.
- Beat schedule uses a **fixed clock time**, `crontab(hour=2, minute=0)` (2:00 AM server time) — not a rolling "every 24 hours from whenever beat started" interval, which drifts and is harder to reason about for monitoring.
- Task execution in tests uses `CELERY_TASK_ALWAYS_EAGER = True`, set via an `autouse` pytest fixture in a root `conftest.py` — no test suite requires a real broker or worker process running.

## Files
- `config/celery.py`
- `config/__init__.py` (edit)
- `config/settings.py` (edit: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CELERY_TASK_ROUTES`, `CELERY_BEAT_SCHEDULE`)
- `advisor/tasks.py`
- `transactions/categorization.py` (edit: replace the Tier-3 placeholder comment from Sprint 8 with the real dispatch call)
- `conftest.py` (new, project root)
- `advisor/tests/test_tasks.py`

## Classes & Functions
`config/celery.py`:
```python
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

`config/settings.py` additions:
```python
from celery.schedules import crontab

CELERY_BROKER_URL = env("REDIS_URL")
CELERY_RESULT_BACKEND = env("REDIS_URL")
CELERY_TASK_ROUTES = {
    "advisor.tasks.run_daily_insights": {"queue": "llm"},
    "advisor.tasks.categorize_with_llm": {"queue": "llm"},
}
CELERY_BEAT_SCHEDULE = {
    "nightly-insights": {
        "task": "advisor.tasks.run_daily_insights",
        "schedule": crontab(hour=2, minute=0),
    },
}
```

`advisor/tasks.py`:
```python
from datetime import date
from celery import shared_task
from django.contrib.auth import get_user_model
from .rules import run_rules_for_user
from .ai import generate_advice, categorize_via_llm

@shared_task(acks_late=True, retry_backoff=True, max_retries=3)
def run_daily_insights():
    today = date.today()
    for user in get_user_model().objects.filter(is_active=True):
        for insight in run_rules_for_user(user, today.replace(day=1), today):
            try:
                generate_advice(insight)
            except Exception:
                pass

@shared_task(acks_late=True, retry_backoff=True, max_retries=3)
def categorize_with_llm(transaction_id):
    from transactions.models import Transaction
    txn = Transaction.objects.select_related("user").get(id=transaction_id)
    categorize_via_llm(txn)
```

`transactions/categorization.py` edit — inside `categorize()`, replace the Sprint 8 placeholder comment with:
```python
    from advisor.tasks import categorize_with_llm
    categorize_with_llm.delay(transaction.id)
```

`conftest.py`:
```python
import pytest

@pytest.fixture(autouse=True)
def celery_eager(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
```

## Task Breakdown
1. Confirm `celery` and `redis` (Python packages) are installed — both were in Sprint 1's initial `pip install` line
2. Write `config/celery.py`
3. Edit `config/__init__.py`: `from .celery import app as celery_app` / `__all__ = ("celery_app",)`
4. Edit `config/settings.py`: add `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CELERY_TASK_ROUTES`, `CELERY_BEAT_SCHEDULE` exactly as above
5. Write `advisor/tasks.py`
6. Edit `transactions/categorization.py`: wire the Tier-3 dispatch call
7. Write `conftest.py` at the project root
8. Write `advisor/tests/test_tasks.py`
9. Locally, run all three processes in separate terminals to confirm end-to-end behavior:
   ```bash
   celery -A config worker -Q default -c 4 -l info
   celery -A config worker -Q llm -c 1 -l info
   celery -A config beat -l info
   ```

## Testing Plan
`advisor/tests/test_tasks.py` (all run via `.apply()` — Celery's standard synchronous-in-test-process pattern, no broker needed thanks to the eager-mode fixture):
- `test_run_daily_insights_only_processes_active_users` — mock Ollama via `responses`; create an over-budget scenario for an active user AND an equally over-budget scenario for an `is_active=False` user; call `run_daily_insights.apply()`; assert `Insight`/`AdviceMessage` rows exist only for the active user
- `test_categorize_with_llm_task_updates_transaction` — mock Ollama's response to match a real category name; create a transaction with `category=None`; call `categorize_with_llm.apply(args=[txn.id])`; assert the category is set
- `test_categorization_tier3_end_to_end` — with `CELERY_TASK_ALWAYS_EAGER=True` (already the default via the `conftest.py` fixture) and Ollama mocked, create a transaction with a merchant string that matches neither Tier 1 nor Tier 2, call `categorize(txn)` directly; assert the transaction ends up correctly categorized via the full dispatch chain (`categorize()` → `.delay()` → eager execution → `categorize_via_llm`)

## Load & Scale
- This sprint is the concrete enforcement point for the Sprint 0 global decision: the `llm` queue exists specifically so `run_daily_insights` (potentially looping over many users, each generating multiple AI calls) and `categorize_with_llm` (potentially fired many times in a burst during a CSV import in Sprint 14) never run concurrently against the single Ollama/GPU instance — `CELERY_TASK_ROUTES` is what makes this automatic rather than dependent on remembering to route each task correctly by hand later.
- `default` queue's `-c 4` is a placeholder tied to a 4-core assumption — Sprint 17 revisits this against the actual deployment host's core count as part of the `docker-compose.yml` service definitions.
- Retry policy (`acks_late`, `retry_backoff`, `max_retries=3`) means a transient Ollama restart is absorbed automatically; a permanently-failing task still eventually gives up rather than retrying forever and silently consuming worker capacity.

## Definition of Done
- All 3 new tests pass
- With Ollama and both worker processes plus beat running locally: creating a transaction with an unrecognized merchant results in it being auto-categorized within a few seconds, observably running on the `llm` queue (visible in the `-Q llm` worker's log output) rather than `default`
