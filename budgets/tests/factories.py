from decimal import Decimal
import factory
from budgets.models import Budget
from transactions.tests.factories import CategoryFactory


class BudgetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Budget

    category = factory.SubFactory(
        CategoryFactory,
        user=factory.SelfAttribute("..user"),
    )
    monthly_limit = Decimal("5000.00")
