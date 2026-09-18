from datetime import date
from decimal import Decimal
import pytest
from accounts.tests.factories import UserFactory
from budgets.services import get_budget_progress
from budgets.tests.factories import BudgetFactory
from transactions.tests.factories import CategoryFactory, TransactionFactory


@pytest.mark.django_db
def test_get_budget_progress_computes_spent_and_percent():
    user = UserFactory()
    cat = CategoryFactory(user=user, name="Dining")
    budget = BudgetFactory(user=user, category=cat, monthly_limit=Decimal("1000.00"))

    # Add transactions totaling 600 in the target month
    TransactionFactory(user=user, category=cat, amount=Decimal("250.00"), date=date(2026, 9, 5))
    TransactionFactory(user=user, category=cat, amount=Decimal("350.00"), date=date(2026, 9, 12))

    rows = get_budget_progress(user, 2026, 9)
    assert len(rows) == 1
    row = rows[0]
    assert row["budget"] == budget
    assert row["spent"] == Decimal("600.00")
    assert row["pct"] == 60
    assert row["over"] is False


@pytest.mark.django_db
def test_get_budget_progress_flags_over_budget():
    user = UserFactory()
    cat = CategoryFactory(user=user, name="Shopping")
    BudgetFactory(user=user, category=cat, monthly_limit=Decimal("1000.00"))

    # Spend 1200 against 1000 limit
    TransactionFactory(user=user, category=cat, amount=Decimal("1200.00"), date=date(2026, 9, 10))

    rows = get_budget_progress(user, 2026, 9)
    assert len(rows) == 1
    row = rows[0]
    assert row["spent"] == Decimal("1200.00")
    assert row["pct"] == 100  # Capped at 100, not 120
    assert row["over"] is True


@pytest.mark.django_db
def test_get_budget_progress_excludes_other_months():
    user = UserFactory()
    cat = CategoryFactory(user=user, name="Transport")
    BudgetFactory(user=user, category=cat, monthly_limit=Decimal("1000.00"))

    # Transaction in previous month (August 2026)
    TransactionFactory(user=user, category=cat, amount=Decimal("400.00"), date=date(2026, 8, 25))
    # Transaction in target month (September 2026)
    TransactionFactory(user=user, category=cat, amount=Decimal("150.00"), date=date(2026, 9, 5))

    rows = get_budget_progress(user, 2026, 9)
    assert len(rows) == 1
    row = rows[0]
    assert row["spent"] == Decimal("150.00")
    assert row["pct"] == 15
    assert row["over"] is False
