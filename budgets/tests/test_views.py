import pytest
from django.core.cache import cache
from django.urls import reverse
from accounts.tests.factories import UserFactory
from budgets import views
from budgets.tests.factories import BudgetFactory


@pytest.mark.django_db
def test_progress_partial_requires_login(client):
    url = reverse("budgets:progress_partial")
    response = client.get(url)
    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_progress_partial_caches_result(client, mocker):
    cache.clear()
    user = UserFactory()
    client.force_login(user)
    BudgetFactory(user=user)

    spy = mocker.spy(views, "get_budget_progress")

    url = reverse("budgets:progress_partial")

    # First request: cache miss, invokes get_budget_progress
    resp1 = client.get(url)
    assert resp1.status_code == 200
    assert spy.call_count == 1

    # Second request: served from cache
    resp2 = client.get(url)
    assert resp2.status_code == 200
    assert spy.call_count == 1
