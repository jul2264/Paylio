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


@pytest.mark.django_db
def test_budget_list_renders_budgets(client):
    from decimal import Decimal
    from transactions.tests.factories import CategoryFactory

    user = UserFactory()
    client.force_login(user)
    cat = CategoryFactory(user=user, name="Dining")
    BudgetFactory(user=user, category=cat, monthly_limit=Decimal("5000.00"))

    url = reverse("budgets:list")
    response = client.get(url)

    assert response.status_code == 200
    assert "Dining" in response.content.decode()
    assert "5000.00" in response.content.decode()


@pytest.mark.django_db
def test_budget_create_view_creates_and_invalidates_cache(client):
    from decimal import Decimal
    from budgets.models import Budget
    from transactions.tests.factories import CategoryFactory

    user = UserFactory()
    client.force_login(user)
    cat = CategoryFactory(user=user, name="Groceries", kind="EXPENSE")

    url = reverse("budgets:create")
    response = client.post(url, {"category": cat.id, "monthly_limit": "8000.00"})

    assert response.status_code == 302
    assert response.url == reverse("budgets:list")
    assert Budget.objects.filter(user=user, category=cat, monthly_limit=Decimal("8000.00")).exists()


@pytest.mark.django_db
def test_budget_delete_view_removes_budget(client):
    from budgets.models import Budget

    user = UserFactory()
    client.force_login(user)
    budget = BudgetFactory(user=user)

    url = reverse("budgets:delete", kwargs={"pk": budget.id})
    response = client.post(url)

    assert response.status_code == 302
    assert response.url == reverse("budgets:list")
    assert not Budget.objects.filter(id=budget.id).exists()
