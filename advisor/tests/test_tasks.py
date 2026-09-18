from datetime import date
from decimal import Decimal
import pytest
import responses
from django.conf import settings
from accounts.tests.factories import UserFactory
from advisor.models import AdviceMessage, Insight
from advisor.tasks import categorize_with_llm, run_daily_insights
from budgets.tests.factories import BudgetFactory
from transactions.categorization import categorize
from transactions.tests.factories import CategoryFactory, TransactionFactory


@pytest.mark.django_db
@responses.activate
def test_run_daily_insights_only_processes_active_users():
    user_active = UserFactory(username="active_user", is_active=True)
    user_inactive = UserFactory(username="inactive_user", is_active=False)

    # Active user over-budget scenario
    cat_active = CategoryFactory(user=user_active, name="Dining")
    BudgetFactory(user=user_active, category=cat_active, monthly_limit=Decimal("1000.00"))
    TransactionFactory(user=user_active, category=cat_active, amount=Decimal("1500.00"), date=date.today())

    # Inactive user over-budget scenario
    cat_inactive = CategoryFactory(user=user_inactive, name="Dining")
    BudgetFactory(user=user_inactive, category=cat_inactive, monthly_limit=Decimal("1000.00"))
    TransactionFactory(user=user_inactive, category=cat_inactive, amount=Decimal("1500.00"), date=date.today())

    endpoint = f"{settings.OLLAMA_HOST}/api/chat"
    responses.add(
        responses.POST,
        endpoint,
        json={"message": {"content": "You are over budget on dining."}},
        status=200,
    )

    run_daily_insights.apply()

    assert Insight.objects.filter(user=user_active).count() >= 1
    assert AdviceMessage.objects.filter(insight__user=user_active).count() >= 1
    assert Insight.objects.filter(user=user_inactive).count() == 0
    assert AdviceMessage.objects.filter(insight__user=user_inactive).count() == 0


@pytest.mark.django_db
@responses.activate
def test_categorize_with_llm_task_updates_transaction():
    user = UserFactory()
    cat = CategoryFactory(user=user, name="Groceries")
    txn = TransactionFactory(user=user, merchant="Local Bazaar", category=None)

    endpoint = f"{settings.OLLAMA_HOST}/api/chat"
    responses.add(
        responses.POST,
        endpoint,
        json={"message": {"content": "Groceries"}},
        status=200,
    )

    categorize_with_llm.apply(args=[txn.id])
    txn.refresh_from_db()

    assert txn.category == cat


@pytest.mark.django_db
@responses.activate
def test_categorization_tier3_end_to_end():
    user = UserFactory()
    cat = CategoryFactory(user=user, name="Shopping")
    txn = TransactionFactory(user=user, merchant="Unique Unknown Brand", category=None)

    endpoint = f"{settings.OLLAMA_HOST}/api/chat"
    responses.add(
        responses.POST,
        endpoint,
        json={"message": {"content": "Shopping"}},
        status=200,
    )

    # End-to-end execution: categorize() -> .delay() -> eager task -> categorize_via_llm
    categorize(txn)
    txn.refresh_from_db()

    assert txn.category == cat
