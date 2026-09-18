from datetime import date
from decimal import Decimal
import pytest
from accounts.tests.factories import UserFactory
from dashboard.services import get_monthly_summary
from transactions.tests.factories import CategoryFactory, TransactionFactory


@pytest.mark.django_db
def test_get_monthly_summary_totals_correctly():
    user = UserFactory()
    cat_food = CategoryFactory(user=user, name="Food")
    cat_travel = CategoryFactory(user=user, name="Travel")
    today = date.today()

    TransactionFactory(user=user, category=cat_food, amount=Decimal("100.50"), date=today)
    TransactionFactory(user=user, category=cat_food, amount=Decimal("50.25"), date=today)
    TransactionFactory(user=user, category=cat_travel, amount=Decimal("200.00"), date=today)

    summary = get_monthly_summary(user, today.year, today.month)

    assert summary["total_spent"] == Decimal("350.75")
    assert len(summary["by_category"]) == 2

    # Ordered descending by total
    assert summary["by_category"][0]["category__name"] == "Travel"
    assert summary["by_category"][0]["total"] == Decimal("200.00")
    assert summary["by_category"][1]["category__name"] == "Food"
    assert summary["by_category"][1]["total"] == Decimal("150.75")


@pytest.mark.django_db
def test_get_monthly_summary_excludes_other_months():
    user = UserFactory()
    cat = CategoryFactory(user=user, name="Bills")

    # Current month transaction
    today = date.today()
    TransactionFactory(user=user, category=cat, amount=Decimal("500.00"), date=today)

    # Previous month transaction
    prev_month = 12 if today.month == 1 else today.month - 1
    prev_year = today.year - 1 if today.month == 1 else today.year
    prev_date = date(prev_year, prev_month, 15)
    TransactionFactory(user=user, category=cat, amount=Decimal("800.00"), date=prev_date)

    summary = get_monthly_summary(user, today.year, today.month)

    assert summary["total_spent"] == Decimal("500.00")
    assert len(summary["by_category"]) == 1
    assert summary["by_category"][0]["total"] == Decimal("500.00")


@pytest.mark.django_db
def test_get_monthly_summary_no_transactions_returns_zero():
    user = UserFactory()
    today = date.today()

    summary = get_monthly_summary(user, today.year, today.month)

    assert summary["total_spent"] == Decimal("0")
    assert summary["by_category"] == []
