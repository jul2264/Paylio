# Sprint 10 — Robo-Advisor: Rule Engine

**Duration: 3 days.**

## Objective
Deterministic Python rules that detect spending issues and record them as `Insight` rows — the "facts" half of the hybrid rule+LLM advisor. No AI call happens in this sprint; that's Sprint 11.

## Preconditions
Sprints 4 and 8 complete.

## Firm Decisions
- **Both** `Insight` and `AdviceMessage` models are created in this single sprint/migration, even though `AdviceMessage.body` isn't populated until Sprint 11 — `AdviceMessage.insight` is a `ForeignKey` with `related_name="advice"` that `Insight` needs to exist for; splitting the two models across two separate migrations for no functional reason adds risk for no benefit.
- **Exactly two rules ship in this sprint**: `BudgetOverspendRule` and `TrendIncreaseRule`. `SavingsRateDropRule`, `RecurringCreepRule`, and `UnusualTransactionRule` are explicitly **out of scope** — noted as backlog candidates, not designed here, to avoid scope creep beyond the 19-step plan as given.
- `TrendIncreaseRule` threshold is fixed at **30%** above the trailing 3-month average — not configurable per user in v1.
- Trailing-average calculation is done in Python after three simple aggregate queries (not a single window-function query) — chosen for readability and correctness confidence over shaving query count, given the data volumes involved.
- Rules are **never** called from a request-handling view directly (not from the dashboard, not from any HTMX partial) — the only call sites are Sprint 12's "Refresh insights" button and Sprint 13's nightly Celery task.

## Files
- `advisor/models.py`
- `advisor/admin.py`
- `advisor/migrations/0001_initial.py` (generated)
- `advisor/rules.py`
- `advisor/tests/factories.py`
- `advisor/tests/test_rules.py`

## Classes & Functions
`advisor/models.py`:
```python
from django.conf import settings
from django.db import models
from transactions.models import Category

class Insight(models.Model):
    INFO, WARNING, CRITICAL = "INFO", "WARNING", "CRITICAL"
    SEVERITY_CHOICES = [(INFO, "Info"), (WARNING, "Warning"), (CRITICAL, "Critical")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rule_key = models.CharField(max_length=50)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
    period_start = models.DateField()
    period_end = models.DateField()
    summary = models.CharField(max_length=255)
    raw_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

class AdviceMessage(models.Model):
    insight = models.ForeignKey(Insight, on_delete=models.CASCADE, related_name="advice")
    body = models.TextField()
    model_used = models.CharField(max_length=50)
    user_feedback = models.CharField(max_length=15, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

`advisor/rules.py` — `BaseRule`, `BudgetOverspendRule`, `TrendIncreaseRule`, `RULES`, `run_rules_for_user(user, period_start, period_end)` — exact implementation as specified in `spending-tracker-architecture.md` Step 10 (trailing-average logic uses `dateutil.relativedelta`).

## Task Breakdown
1. `pip install python-dateutil`, add to `requirements.txt`
2. Write `advisor/models.py` — both models exactly as above
3. Write `advisor/admin.py` — register `Insight` and `AdviceMessage`
4. `python manage.py makemigrations advisor && python manage.py migrate`
5. Write `advisor/rules.py` — `BaseRule`, `BudgetOverspendRule`, `TrendIncreaseRule`, `RULES = [BudgetOverspendRule(), TrendIncreaseRule()]`, `run_rules_for_user`
6. Write `advisor/tests/factories.py` — `InsightFactory`
7. Write `advisor/tests/test_rules.py`

## Testing Plan
All tests use `freezegun.freeze_time(...)` to fix "today" to a known date, so trailing-month math is deterministic.

`advisor/tests/test_rules.py`:
- `test_budget_overspend_rule_fires_when_over` — budget limit ₹1000, this-month spend ₹1200 in that category, assert an `Insight` is created with `raw_data == {"spent": 1200.0, "limit": 1000.0, "pct_over": 20}`
- `test_budget_overspend_rule_silent_when_under` — spend ₹800 vs ₹1000 limit, assert no `Insight` created
- `test_trend_increase_rule_fires_above_threshold` — 3 trailing months averaging ₹1000/month in a category, current month ₹1500 (50% increase, above the 30% threshold), assert an `Insight` fires with the correct `pct_increase`
- `test_trend_increase_rule_silent_below_threshold` — current month ₹1200 (20% increase, below threshold), assert no `Insight`
- `test_trend_increase_rule_handles_zero_trailing_average` — a category with transactions only in the current month (no trailing history), assert no crash and no `Insight` (the `avg > 0` guard is exercised)
- `test_run_rules_for_user_aggregates_both_rules` — a scenario that triggers both rules simultaneously, assert `run_rules_for_user` returns insights from both `rule_key` values

## Load & Scale
- `TrendIncreaseRule` issues up to 4 aggregate queries per distinct category the user has ever transacted in (current month + 3 trailing months) — for ~10 categories, up to 40 small queries per run. Acceptable because rules run on-demand (Sprint 12's button) or once nightly per user (Sprint 13's Celery Beat schedule), never on every page load.
- `Insight`/`AdviceMessage` rows accumulate with no retention policy in v1 — a deliberate deferral. If table growth becomes a measurable problem later, the fix is a Celery Beat task pruning `Insight` rows older than a fixed window (e.g. 180 days); not built now.

## Definition of Done
- All 6 tests pass
- Manual smoke test via `python manage.py shell`: seed an over-budget scenario for the superuser, run `from advisor.rules import run_rules_for_user; from datetime import date; run_rules_for_user(user, date.today().replace(day=1), date.today())`, confirm `Insight.objects.all()` shows the expected row
