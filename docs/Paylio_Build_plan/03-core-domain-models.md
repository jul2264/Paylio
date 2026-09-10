# Sprint 3 — Core Domain Models

**Duration: 2 days.**

## Objective
Build the four tables everything else in the project reads or writes: `Category`, `FinancialAccount`, `Transaction`, `UserMerchantCategory`. Nothing past this sprint can be built until these exist.

## Preconditions
Sprint 2 complete (`AUTH_USER_MODEL` live, at least one migration already applied).

## Firm Decisions
- Categories are **per-user**, not global — `unique_together = ("user", "name")`. No shared/system category table in v1.
- Hard delete only. No soft-delete/`is_deleted` flag on any model in v1 — adds complexity (every query needs a filter) for no concrete requirement yet.
- `amount` is always positive; sign/direction comes from `category.kind` (INCOME/EXPENSE), never from the sign of the number. This avoids a whole class of double-negative bugs in aggregation queries later.
- `external_id` + a partial unique constraint (`condition=Q(external_id__isnull=False)`) is the dedupe mechanism for bank-sync and CSV import (Sprints 14–15) — decided now because retrofitting a uniqueness constraint onto a table that already has data is a migration headache; it costs nothing to add on an empty table.
- Currency is INR-only in v1 — `FinancialAccount.currency` field exists (for schema stability) but every part of the app assumes INR; no multi-currency conversion logic anywhere.

## Files
- `transactions/models.py`
- `transactions/admin.py`
- `transactions/migrations/0001_initial.py` (generated)
- `transactions/tests/factories.py`
- `transactions/tests/test_models.py`

## Classes & Functions

`transactions/models.py`:
```python
from django.conf import settings
from django.db import models


class Category(models.Model):
    INCOME, EXPENSE = "INCOME", "EXPENSE"
    KIND_CHOICES = [(INCOME, "Income"), (EXPENSE, "Expense")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL)
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default=EXPENSE)

    class Meta:
        unique_together = ("user", "name")

    def __str__(self):
        return self.name


class FinancialAccount(models.Model):
    CHECKING, SAVINGS, CREDIT_CARD, CASH = "CHECKING", "SAVINGS", "CREDIT_CARD", "CASH"
    TYPE_CHOICES = [(CHECKING, "Checking"), (SAVINGS, "Savings"), (CREDIT_CARD, "Credit Card"), (CASH, "Cash")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    account_type = models.CharField(max_length=15, choices=TYPE_CHOICES)
    currency = models.CharField(max_length=3, default="INR")

    def __str__(self):
        return self.name


class Transaction(models.Model):
    MANUAL, BANK_SYNC = "MANUAL", "BANK_SYNC"
    SOURCE_CHOICES = [(MANUAL, "Manual"), (BANK_SYNC, "Bank Sync")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    account = models.ForeignKey(FinancialAccount, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    merchant = models.CharField(max_length=200, blank=True)
    description = models.CharField(max_length=255, blank=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=MANUAL)
    external_id = models.CharField(max_length=200, null=True, blank=True)
    is_recurring = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "date"]),
            models.Index(fields=["user", "category", "date"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["account", "external_id"],
                name="unique_external_txn_per_account",
                condition=models.Q(external_id__isnull=False),
            )
        ]

    def __str__(self):
        return f"{self.merchant} - {self.amount}"


class UserMerchantCategory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    merchant_normalized = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("user", "merchant_normalized")
```

## Task Breakdown
1. Write the four model classes above exactly as specified
2. `transactions/admin.py` — register all four with `admin.site.register(...)`
3. `python manage.py makemigrations transactions`
4. `python manage.py migrate`
5. Through `/admin/`, seed these exact categories for the superuser account (used as fixed test data across every later sprint, including the categorization keyword table in Sprint 8, which is written to match these names exactly): `Food & Dining` (EXPENSE), `Transport` (EXPENSE), `Shopping` (EXPENSE), `Subscriptions` (EXPENSE), `Utilities` (EXPENSE), `Salary` (INCOME). Seed one `FinancialAccount`: name "Primary Checking", `account_type=CHECKING`.
6. `transactions/tests/factories.py` — `CategoryFactory`, `FinancialAccountFactory`, `TransactionFactory` (with `account=SubFactory(FinancialAccountFactory)`, `category=SubFactory(CategoryFactory)`), `UserMerchantCategoryFactory`. All four factories accept `user` as a required param (no default `UserFactory()` call baked in) so tests explicitly control which user owns which row — this matters for the cross-user isolation test below.
7. `transactions/tests/test_models.py`

## Testing Plan
`transactions/tests/test_models.py`:
- `test_category_unique_per_user` — create `Category(user=A, name="Food")`, assert creating a second `Category(user=A, name="Food")` raises `IntegrityError`; assert `Category(user=B, name="Food")` succeeds
- `test_transaction_external_id_unique_per_account` — create a transaction with `external_id="TXN123"` on account X, assert a second transaction with the same `external_id` on the same account raises `IntegrityError`; assert two transactions on the same account with `external_id=None` both save successfully (proves the partial-unique condition works as intended)
- `test_transaction_str` — assert `str(txn) == f"{txn.merchant} - {txn.amount}"`
- `test_usermerchantcategory_unique_per_user_merchant` — same pattern as the category test

## Load & Scale
- The two composite indexes (`user, date` and `user, category, date`) exist specifically for the two query shapes Sprint 6 (dashboard aggregation) and Sprint 9 (budget-vs-actual) will run — this sprint doesn't use them yet, but they must be declared here since adding an index to a large production table later is a much heavier operation than adding one to an empty table now.
- Forward decision for Sprint 14 (CSV/bank import): batch inserts will use `Transaction.objects.bulk_create(rows, ignore_conflicts=True)`, not per-row `.save()` in a loop — the `external_id` unique constraint defined here is exactly what makes `ignore_conflicts=True` safe (duplicate rows are silently skipped by Postgres rather than raising and aborting the whole batch).

## Definition of Done
- All 4 tests pass
- `/admin/` shows all four models with the seed data from step 5 present
- `python manage.py makemigrations --check --dry-run` is clean
