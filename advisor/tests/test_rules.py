from datetime import date
from decimal import Decimal
import pytest
from freezegun import freeze_time
from accounts.tests.factories import UserFactory
from advisor.models import Insight
from advisor.rules import (
    BudgetOverspendRule,
    TrendIncreaseRule,
    run_rules_for_user,
)
from budgets.tests.factories import BudgetFactory
from transactions.tests.factories import CategoryFactory, TransactionFactory


@pytest.mark.django_db
@freeze_time("2026-09-15")
def test_budget_overspend_rule_fires_when_over():
    user = UserFactory()
    cat = CategoryFactory(user=user, name="Dining")
    BudgetFactory(user=user, category=cat, monthly_limit=Decimal("1000.00"))

    # Current month spend of 1200 against 1000 limit
    TransactionFactory(user=user, category=cat, amount=Decimal("1200.00"), date=date(2026, 9, 10))

    rule = BudgetOverspendRule()
    insights = rule.evaluate(user, date(2026, 9, 1), date(2026, 9, 30))

    assert len(insights) == 1
    insight = insights[0]
    assert insight.rule_key == "budget_overspend"
    assert insight.severity == Insight.WARNING
    assert insight.raw_data == {"spent": 1200.0, "limit": 1000.0, "pct_over": 20}
    assert "Dining" in insight.summary


@pytest.mark.django_db
@freeze_time("2026-09-15")
def test_budget_overspend_rule_silent_when_under():
    user = UserFactory()
    cat = CategoryFactory(user=user, name="Dining")
    BudgetFactory(user=user, category=cat, monthly_limit=Decimal("1000.00"))

    # Current month spend of 800 against 1000 limit
    TransactionFactory(user=user, category=cat, amount=Decimal("800.00"), date=date(2026, 9, 10))

    rule = BudgetOverspendRule()
    insights = rule.evaluate(user, date(2026, 9, 1), date(2026, 9, 30))

    assert len(insights) == 0


@pytest.mark.django_db
@freeze_time("2026-09-15")
def test_trend_increase_rule_fires_above_threshold():
    user = UserFactory()
    cat = CategoryFactory(user=user, name="Groceries")

    # 3 trailing months averaging 1000/month (June, July, August 2026)
    TransactionFactory(user=user, category=cat, amount=Decimal("1000.00"), date=date(2026, 6, 15))
    TransactionFactory(user=user, category=cat, amount=Decimal("1000.00"), date=date(2026, 7, 15))
    TransactionFactory(user=user, category=cat, amount=Decimal("1000.00"), date=date(2026, 8, 15))

    # Current month (September 2026): 1500 (50% increase > 30% threshold)
    TransactionFactory(user=user, category=cat, amount=Decimal("1500.00"), date=date(2026, 9, 10))

    rule = TrendIncreaseRule()
    insights = rule.evaluate(user, date(2026, 9, 1), date(2026, 9, 30))

    assert len(insights) == 1
    insight = insights[0]
    assert insight.rule_key == "trend_increase"
    assert insight.severity == Insight.INFO
    assert insight.raw_data == {"current": 1500.0, "trailing_avg": 1000.0, "pct_increase": 50}


@pytest.mark.django_db
@freeze_time("2026-09-15")
def test_trend_increase_rule_silent_below_threshold():
    user = UserFactory()
    cat = CategoryFactory(user=user, name="Groceries")

    # 3 trailing months averaging 1000/month
    TransactionFactory(user=user, category=cat, amount=Decimal("1000.00"), date=date(2026, 6, 15))
    TransactionFactory(user=user, category=cat, amount=Decimal("1000.00"), date=date(2026, 7, 15))
    TransactionFactory(user=user, category=cat, amount=Decimal("1000.00"), date=date(2026, 8, 15))

    # Current month: 1200 (20% increase <= 30% threshold)
    TransactionFactory(user=user, category=cat, amount=Decimal("1200.00"), date=date(2026, 9, 10))

    rule = TrendIncreaseRule()
    insights = rule.evaluate(user, date(2026, 9, 1), date(2026, 9, 30))

    assert len(insights) == 0


@pytest.mark.django_db
@freeze_time("2026-09-15")
def test_trend_increase_rule_handles_zero_trailing_average():
    user = UserFactory()
    cat = CategoryFactory(user=user, name="Electronics")

    # Current month only, no trailing transactions
    TransactionFactory(user=user, category=cat, amount=Decimal("2000.00"), date=date(2026, 9, 10))

    rule = TrendIncreaseRule()
    insights = rule.evaluate(user, date(2026, 9, 1), date(2026, 9, 30))

    assert len(insights) == 0


@pytest.mark.django_db
@freeze_time("2026-09-15")
def test_run_rules_for_user_aggregates_both_rules():
    user = UserFactory()
    cat = CategoryFactory(user=user, name="Shopping")
    BudgetFactory(user=user, category=cat, monthly_limit=Decimal("1000.00"))

    # Trailing 3 months averaging 1000/month
    TransactionFactory(user=user, category=cat, amount=Decimal("1000.00"), date=date(2026, 6, 15))
    TransactionFactory(user=user, category=cat, amount=Decimal("1000.00"), date=date(2026, 7, 15))
    TransactionFactory(user=user, category=cat, amount=Decimal("1000.00"), date=date(2026, 8, 15))

    # Current month: 1600 (both over budget 1000 and 60% over trailing avg 1000)
    TransactionFactory(user=user, category=cat, amount=Decimal("1600.00"), date=date(2026, 9, 10))

    insights = run_rules_for_user(user, date(2026, 9, 1), date(2026, 9, 30))

    rule_keys = {i.rule_key for i in insights}
    assert "budget_overspend" in rule_keys
    assert "trend_increase" in rule_keys
    assert len(insights) == 2
