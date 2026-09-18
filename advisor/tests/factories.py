from datetime import date
import factory
from accounts.tests.factories import UserFactory
from advisor.models import AdviceMessage, Insight
from transactions.tests.factories import CategoryFactory


class InsightFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Insight

    user = factory.SubFactory(UserFactory)
    rule_key = "budget_overspend"
    severity = Insight.WARNING
    category = factory.SubFactory(
        CategoryFactory,
        user=factory.SelfAttribute("..user"),
    )
    period_start = date(2026, 9, 1)
    period_end = date(2026, 9, 30)
    summary = "Spending is over budget"
    raw_data = factory.LazyFunction(lambda: {"spent": 1200.0, "limit": 1000.0, "pct_over": 20})


class AdviceMessageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AdviceMessage

    insight = factory.SubFactory(InsightFactory)
    body = "You have exceeded your dining budget this month."
    model_used = "qwen3:14b"
    user_feedback = None
