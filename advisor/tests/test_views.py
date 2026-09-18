from datetime import date
from decimal import Decimal
import pytest
import responses
from django.conf import settings
from django.urls import reverse
from accounts.tests.factories import UserFactory
from advisor.models import AdviceMessage, Insight
from advisor.tests.factories import AdviceMessageFactory, InsightFactory
from budgets.tests.factories import BudgetFactory
from transactions.tests.factories import CategoryFactory, TransactionFactory


@pytest.mark.django_db
def test_feed_partial_requires_login(client):
    url = reverse("advisor:feed_partial")
    response = client.get(url)
    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_feed_partial_shows_recent_insights_with_advice(client):
    user = UserFactory()
    client.force_login(user)

    insight = InsightFactory(user=user, summary="Transport spend spike detected")
    AdviceMessageFactory(insight=insight, body="Consider using public transit instead of rideshares.")

    url = reverse("advisor:feed_partial")
    response = client.get(url)

    assert response.status_code == 200
    content = response.content.decode()
    assert "Transport spend spike detected" in content
    assert "Consider using public transit instead of rideshares." in content


@pytest.mark.django_db
def test_feed_partial_limits_to_10(client):
    user = UserFactory()
    client.force_login(user)

    for _ in range(12):
        InsightFactory(user=user)

    url = reverse("advisor:feed_partial")
    response = client.get(url)

    assert response.status_code == 200
    assert len(response.context["insights"]) == 10


@pytest.mark.django_db
@responses.activate
def test_refresh_insights_creates_new_insights_and_advice(client):
    user = UserFactory()
    client.force_login(user)

    cat = CategoryFactory(user=user, name="Dining")
    BudgetFactory(user=user, category=cat, monthly_limit=Decimal("1000.00"))
    TransactionFactory(user=user, category=cat, amount=Decimal("1400.00"), date=date.today())

    endpoint = f"{settings.OLLAMA_HOST}/api/chat"
    mock_body = "Your dining budget was exceeded by 40%. Try cooking at home this weekend."
    responses.add(
        responses.POST,
        endpoint,
        json={"message": {"content": mock_body}},
        status=200,
    )

    url = reverse("advisor:refresh")
    response = client.post(url)

    assert response.status_code == 200
    assert Insight.objects.filter(user=user).count() >= 1
    assert AdviceMessage.objects.filter(insight__user=user).count() >= 1
    content = response.content.decode()
    assert mock_body in content


@pytest.mark.django_db
@responses.activate
def test_refresh_insights_survives_ai_failure(client):
    user = UserFactory()
    client.force_login(user)

    cat = CategoryFactory(user=user, name="Dining")
    BudgetFactory(user=user, category=cat, monthly_limit=Decimal("1000.00"))
    TransactionFactory(user=user, category=cat, amount=Decimal("1400.00"), date=date.today())

    endpoint = f"{settings.OLLAMA_HOST}/api/chat"
    responses.add(
        responses.POST,
        endpoint,
        json={"error": "LLM worker crash"},
        status=500,
    )

    url = reverse("advisor:refresh")
    response = client.post(url)

    assert response.status_code == 200
    assert Insight.objects.filter(user=user).count() >= 1
    assert AdviceMessage.objects.filter(insight__user=user).count() == 0
    content = response.content.decode()
    assert "over budget" in content.lower()
