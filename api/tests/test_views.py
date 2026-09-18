from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from accounts.models import User
from advisor.models import Insight
from api.models import DeviceToken
from budgets.models import Budget
from dashboard.services import get_monthly_summary
from rates.models import MetalRateSnapshot
from transactions.models import Category, FinancialAccount, Transaction

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_user(db):
    user = User.objects.create_user(username="testuser", email="test@example.com", password="password123")
    return user


@pytest.fixture
def authenticated_client(api_client, auth_user):
    api_client.force_authenticate(user=auth_user)
    return api_client


@pytest.fixture
def financial_account(auth_user):
    return FinancialAccount.objects.create(
        user=auth_user,
        name="Main Account",
        account_type=FinancialAccount.CHECKING,
        currency="INR",
    )


@pytest.mark.django_db
def test_register_creates_user(api_client):
    payload = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "strongpassword123",
    }
    response = api_client.post("/api/v1/register/", payload)
    assert response.status_code == 201
    assert User.objects.filter(username="newuser").exists()
    assert response.data["username"] == "newuser"
    assert "password" not in response.data


@pytest.mark.django_db
def test_token_obtain_returns_access_and_refresh_tokens(api_client, auth_user):
    payload = {
        "username": "testuser",
        "password": "password123",
    }
    response = api_client.post("/api/v1/token/", payload)
    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data


@pytest.mark.django_db
def test_transaction_list_requires_authentication(api_client):
    response = api_client.get("/api/v1/transactions/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_transaction_list_is_paginated(authenticated_client, auth_user, financial_account):
    today = date.today()
    # Create 60 transactions
    transactions = [
        Transaction(
            user=auth_user,
            account=financial_account,
            amount=Decimal("100.00"),
            date=today - timedelta(days=i),
            merchant=f"Merchant {i}",
        )
        for i in range(60)
    ]
    Transaction.objects.bulk_create(transactions)

    response = authenticated_client.get("/api/v1/transactions/")
    assert response.status_code == 200
    # Crucial pagination contract: count == 60, len(results) == 50
    assert "count" in response.data
    assert response.data["count"] == 60
    assert "results" in response.data
    assert len(response.data["results"]) == 50


@pytest.mark.django_db
def test_transaction_create_via_api_uses_same_categorization_as_web(authenticated_client, auth_user, financial_account):
    # Swiggy is defined in CATEGORY_KEYWORDS -> "Food & Dining"
    payload = {
        "account": financial_account.id,
        "amount": "450.00",
        "date": str(date.today()),
        "merchant": "Swiggy Order #1234",
        "description": "Lunch delivery",
    }
    response = authenticated_client.post("/api/v1/transactions/", payload)
    assert response.status_code == 201

    created_txn = Transaction.objects.get(id=response.data["id"])
    assert created_txn.category is not None
    assert created_txn.category.name == "Food & Dining"
    assert response.data["category_name"] == "Food & Dining"


@pytest.mark.django_db
def test_dashboard_summary_matches_service_function_directly(authenticated_client, auth_user, financial_account):
    today = date.today()
    category = Category.objects.create(user=auth_user, name="Groceries", kind=Category.EXPENSE)
    Transaction.objects.create(
        user=auth_user,
        account=financial_account,
        category=category,
        amount=Decimal("1250.50"),
        date=today,
        merchant="Supermarket",
    )
    Transaction.objects.create(
        user=auth_user,
        account=financial_account,
        category=category,
        amount=Decimal("750.25"),
        date=today,
        merchant="Fruit Mart",
    )

    # Call direct service function
    service_result = get_monthly_summary(auth_user, today.year, today.month)

    # Call API endpoint
    response = authenticated_client.get(f"/api/v1/dashboard/summary/?year={today.year}&month={today.month}")
    assert response.status_code == 200

    api_total = Decimal(str(response.data["total_spent"]))
    assert api_total == service_result["total_spent"]
    assert len(response.data["by_category"]) == len(service_result["by_category"])
    assert response.data["by_category"][0]["category__name"] == "Groceries"
    assert Decimal(str(response.data["by_category"][0]["total"])) == service_result["by_category"][0]["total"]


@pytest.mark.django_db
def test_metal_rates_endpoint_is_public(api_client):
    # Unauthenticated GET
    MetalRateSnapshot.objects.create(
        metal="GOLD",
        price_per_gram_999=Decimal("7200.00"),
    )
    MetalRateSnapshot.objects.create(
        metal="SILVER",
        price_per_gram_999=Decimal("85.00"),
    )
    MetalRateSnapshot.objects.create(
        metal="PLATINUM",
        price_per_gram_999=Decimal("3100.00"),
    )

    response = api_client.get("/api/v1/rates/")
    assert response.status_code == 200
    assert "gold" in response.data
    assert "24K" in response.data["gold"]
    assert response.data["gold"]["24K"] == 7200.0
    assert "silver" in response.data
    assert "platinum" in response.data
    assert response.data["last_updated"] is not None


@pytest.mark.django_db
def test_device_token_registration(authenticated_client, auth_user):
    payload = {"expo_push_token": "ExponentPushToken[xxxxxxxxxxxxxx]"}
    response = authenticated_client.post("/api/v1/device-token/", payload)
    assert response.status_code == 201
    assert DeviceToken.objects.filter(user=auth_user, expo_push_token="ExponentPushToken[xxxxxxxxxxxxxx]").exists()

    # Re-registering existing token should return 200 OK
    response = authenticated_client.post("/api/v1/device-token/", payload)
    assert response.status_code == 200


@pytest.mark.django_db
def test_advisor_feed_and_refresh(authenticated_client, auth_user):
    today = date.today()
    Insight.objects.create(
        user=auth_user,
        rule_key="budget_overspend",
        severity=Insight.WARNING,
        period_start=today.replace(day=1),
        period_end=today,
        summary="You have spent 95% of your Dining budget.",
        raw_data={"spent": 9500, "limit": 10000},
    )

    response = authenticated_client.get("/api/v1/advisor/feed/")
    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["rule_key"] == "budget_overspend"
    assert response.data[0]["severity"] == "WARNING"


@pytest.mark.django_db
def test_push_notification_dispatch_on_critical_insight(auth_user):
    DeviceToken.objects.create(user=auth_user, expo_push_token="ExponentPushToken[test12345]")
    today = date.today()
    critical_insight = Insight.objects.create(
        user=auth_user,
        rule_key="budget_overspend",
        severity=Insight.CRITICAL,
        period_start=today.replace(day=1),
        period_end=today,
        summary="Critical budget breach!",
        raw_data={},
    )

    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None

        from api.notifications import send_push_notification_for_insight
        send_push_notification_for_insight(auth_user, critical_insight)

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["json"][0]["to"] == "ExponentPushToken[test12345]"
        assert kwargs["json"][0]["title"] == "Paylio Advisor Alert"
        assert kwargs["json"][0]["body"] == "Critical budget breach!"
