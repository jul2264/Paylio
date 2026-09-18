from datetime import date
from decimal import Decimal
import pytest
from django.core.cache import cache
from django.urls import reverse
from accounts.tests.factories import UserFactory
from dashboard import views
from transactions.tests.factories import CategoryFactory, TransactionFactory


@pytest.mark.django_db
def test_dashboard_requires_login(client):
    url = reverse("dashboard")
    response = client.get(url)
    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_dashboard_renders_summary(client):
    cache.clear()
    user = UserFactory(username="dashuser")
    client.force_login(user)

    cat = CategoryFactory(user=user, name="Dining")
    TransactionFactory(user=user, category=cat, amount=Decimal("450.00"), date=date.today())

    url = reverse("dashboard")
    response = client.get(url)

    assert response.status_code == 200
    content = response.content.decode()
    assert "450.00" in content
    assert "categoryChart" in content
    assert "Dining" in content


@pytest.mark.django_db
def test_dashboard_caches_result(client, mocker):
    cache.clear()
    user = UserFactory(username="cacheuser")
    client.force_login(user)

    spy = mocker.spy(views, "get_monthly_summary")

    url = reverse("dashboard")

    # First request: cache miss, executes service call
    resp1 = client.get(url)
    assert resp1.status_code == 200
    assert spy.call_count == 1

    # Second request: served directly from cache
    resp2 = client.get(url)
    assert resp2.status_code == 200
    assert spy.call_count == 1
