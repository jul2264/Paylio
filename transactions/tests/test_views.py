from datetime import date
from decimal import Decimal
import pytest
from django.core.cache import cache
from django.urls import reverse
from accounts.tests.factories import UserFactory
from transactions.models import Transaction, UserMerchantCategory
from transactions.tests.factories import CategoryFactory, FinancialAccountFactory, TransactionFactory


@pytest.mark.django_db
def test_transaction_list_requires_login(client):
    url = reverse("transactions:list")
    response = client.get(url)
    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_transaction_create_saves_and_returns_row(client):
    user = UserFactory()
    client.force_login(user)
    account = FinancialAccountFactory(user=user)
    category = CategoryFactory(user=user)

    url = reverse("transactions:create")
    data = {
        "account": account.id,
        "category": category.id,
        "amount": "349.50",
        "date": "2026-09-15",
        "merchant": "Swiggy",
        "description": "Lunch delivery",
    }
    response = client.post(url, data)

    assert response.status_code == 200
    assert Transaction.objects.filter(user=user).count() == 1
    txn = Transaction.objects.get(user=user)
    assert txn.merchant == "Swiggy"
    assert txn.amount == Decimal("349.50")
    assert "Swiggy" in response.content.decode()


@pytest.mark.django_db
def test_transaction_create_invalid_returns_errors(client):
    user = UserFactory()
    client.force_login(user)
    account = FinancialAccountFactory(user=user)

    url = reverse("transactions:create")
    # Date is omitted
    data = {
        "account": account.id,
        "amount": "250.00",
        "merchant": "Incomplete Store",
    }
    response = client.post(url, data)

    assert response.status_code == 200
    assert Transaction.objects.count() == 0
    content = response.content.decode()
    assert "date" in content.lower() or "required" in content.lower() or "error" in content.lower()


@pytest.mark.django_db
def test_transaction_create_invalidates_dashboard_cache(client):
    user = UserFactory()
    client.force_login(user)
    account = FinancialAccountFactory(user=user)

    cache_key = f"dashboard:{user.id}:2026-9"
    cache.set(cache_key, {"summary": "stale_data"}, 300)
    assert cache.get(cache_key) is not None

    url = reverse("transactions:create")
    data = {
        "account": account.id,
        "amount": "500.00",
        "date": "2026-09-15",
        "merchant": "BigBasket",
    }
    response = client.post(url, data)
    assert response.status_code == 200
    assert cache.get(cache_key) is None


@pytest.mark.django_db
def test_transaction_create_sends_htmx_trigger_header(client):
    user = UserFactory()
    client.force_login(user)
    account = FinancialAccountFactory(user=user)

    url = reverse("transactions:create")
    data = {
        "account": account.id,
        "amount": "199.00",
        "date": "2026-09-15",
        "merchant": "BookMyShow",
    }
    response = client.post(url, data)

    assert response.status_code == 200
    assert response.headers.get("HX-Trigger") == "transactionsChanged" or response.get("HX-Trigger") == "transactionsChanged"


@pytest.mark.django_db
def test_transaction_table_partial_filters_by_category(client):
    user = UserFactory()
    client.force_login(user)
    cat1 = CategoryFactory(user=user, name="Dining")
    cat2 = CategoryFactory(user=user, name="Commute")

    TransactionFactory(user=user, category=cat1, merchant="Swiggy", date=date(2026, 9, 1))
    TransactionFactory(user=user, category=cat2, merchant="Uber", date=date(2026, 9, 2))

    url = reverse("transactions:table_partial")
    response = client.get(url, {"category": cat1.id})

    assert response.status_code == 200
    content = response.content.decode()
    assert "Swiggy" in content
    assert "Uber" not in content


@pytest.mark.django_db
def test_transaction_table_partial_caps_at_100(client):
    user = UserFactory()
    client.force_login(user)
    account = FinancialAccountFactory(user=user)

    # Bulk create 105 transactions
    TransactionFactory.create_batch(105, user=user, account=account)

    url = reverse("transactions:table_partial")
    response = client.get(url)

    assert response.status_code == 200
    assert len(response.context["transactions"]) == 100


@pytest.mark.django_db
def test_recategorize_updates_category_and_learns_mapping(client):
    user = UserFactory()
    client.force_login(user)
    cat_old = CategoryFactory(user=user, name="Old Category")
    cat_new = CategoryFactory(user=user, name="New Category")
    txn = TransactionFactory(user=user, category=cat_old, merchant="Custom Store")

    url = reverse("transactions:recategorize", kwargs={"pk": txn.id})
    response = client.post(url, {"category": cat_new.id})

    assert response.status_code == 200
    txn.refresh_from_db()
    assert txn.category == cat_new
    assert UserMerchantCategory.objects.filter(
        user=user, merchant_normalized="custom store", category=cat_new
    ).exists()


@pytest.mark.django_db
def test_recategorize_rejects_other_users_transaction(client):
    user_a = UserFactory(username="user_a")
    user_b = UserFactory(username="user_b")
    client.force_login(user_b)

    cat_a = CategoryFactory(user=user_a, name="Cat A")
    cat_b = CategoryFactory(user=user_b, name="Cat B")
    txn_a = TransactionFactory(user=user_a, category=cat_a, merchant="Store A")

    url = reverse("transactions:recategorize", kwargs={"pk": txn_a.id})
    response = client.post(url, {"category": cat_b.id})

    assert response.status_code == 404
