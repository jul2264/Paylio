# Sprint 4 — Budgets App

**Duration: 1 day.**

## Objective
One model: a per-category monthly spending limit. Small on purpose — everything budget-related that needs UI or computation is Sprint 9, not this one.

## Preconditions
Sprint 3 complete (`Category` model exists).

## Firm Decisions
- Monthly-recurring only. No date-ranged or one-off budgets in v1 — `Budget` has no `start_date`/`end_date`, it's a standing limit re-evaluated against "this calendar month" every time it's read (the evaluation logic lives in Sprint 9, not here).
- One budget per `(user, category)` — editing means updating the existing row in place, not creating a new versioned one. No budget history/audit trail in v1.

## Files
- `budgets/models.py`
- `budgets/admin.py`
- `budgets/migrations/0001_initial.py` (generated)
- `budgets/tests/factories.py`
- `budgets/tests/test_models.py`

## Classes & Functions
`budgets/models.py`:
```python
from django.conf import settings
from django.db import models
from transactions.models import Category


class Budget(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    monthly_limit = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = ("user", "category")

    def __str__(self):
        return f"{self.category} — ₹{self.monthly_limit}/mo"
```

## Task Breakdown
1. Write `Budget` model exactly as above
2. `budgets/admin.py` — `admin.site.register(Budget)`
3. `python manage.py makemigrations budgets`
4. `python manage.py migrate`
5. Through `/admin/`, seed budgets for the superuser against 3 of the 6 categories from Sprint 3: `Food & Dining` → ₹8000, `Transport` → ₹3000, `Shopping` → ₹5000
6. `budgets/tests/factories.py` — `BudgetFactory`, `category=SubFactory(CategoryFactory)` from `transactions.tests.factories`
7. `budgets/tests/test_models.py`

## Testing Plan
`budgets/tests/test_models.py`:
- `test_budget_unique_per_user_category` — create `Budget(user=A, category=C, monthly_limit=5000)`, assert a second `Budget(user=A, category=C, ...)` raises `IntegrityError`
- `test_budget_str` — assert the `__str__` output matches the `f"{category} — ₹{monthly_limit}/mo"` format exactly

## Load & Scale
None new this sprint. Row count per user is bounded by category count (typically under 20), so no indexing decision is needed beyond what `unique_together` already creates.

## Definition of Done
- Both tests pass
- `/admin/` shows the 3 seeded budgets correctly linked to their categories
- `makemigrations --check --dry-run` clean
