from decimal import Decimal
import pytest
from django.db import IntegrityError, transaction
from accounts.tests.factories import UserFactory
from budgets.models import Budget
from budgets.tests.factories import BudgetFactory
from transactions.tests.factories import CategoryFactory


@pytest.mark.django_db
def test_budget_unique_per_user_category():
    user = UserFactory()
    category = CategoryFactory(user=user)

    Budget.objects.create(user=user, category=category, monthly_limit=Decimal("5000.00"))

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Budget.objects.create(user=user, category=category, monthly_limit=Decimal("7500.00"))

    other_user = UserFactory()
    other_category = CategoryFactory(user=other_user)
    other_budget = Budget.objects.create(
        user=other_user,
        category=other_category,
        monthly_limit=Decimal("5000.00"),
    )
    assert other_budget.pk is not None


@pytest.mark.django_db
def test_budget_str():
    user = UserFactory()
    category = CategoryFactory(user=user, name="Groceries")
    budget = BudgetFactory(user=user, category=category, monthly_limit=Decimal("8000.00"))

    assert str(budget) == "Groceries — ₹8000.00/mo"
