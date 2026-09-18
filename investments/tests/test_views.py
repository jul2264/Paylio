from datetime import timedelta
from unittest.mock import patch
from django.urls import reverse
from django.utils import timezone
import django_otp
from django_otp.plugins.otp_totp.models import TOTPDevice
import pytest
from accounts.tests.factories import UserFactory
from investments.models import BrokerConnection
from investments.tests.factories import BrokerConnectionFactory, HoldingFactory


@pytest.mark.django_db
def test_connect_broker_requires_otp(client):
    user = UserFactory()
    client.force_login(user)

    url = reverse("investments:connect")
    response = client.get(url)

    # Without OTP verification, user is redirected to otp_setup
    assert response.status_code == 302
    assert reverse("otp_setup") in response.url


@pytest.mark.django_db
def test_broker_callback_stores_encrypted_token(client):
    user = UserFactory()
    client.force_login(user)

    # Establish verified OTP in the test client session
    device = TOTPDevice.objects.create(user=user, name="default", confirmed=True)
    session = client.session
    session[django_otp.DEVICE_ID_SESSION_KEY] = device.persistent_id
    session.save()

    url = reverse("investments:callback")
    with patch(
        "investments.views.exchange_request_token",
        return_value="super_secret_kite_access_token_xyz",
    ) as mock_exchange:
        response = client.get(url, {"request_token": "valid_req_token_123"})
        mock_exchange.assert_called_once_with("valid_req_token_123")

    assert response.status_code == 302
    assert response.url == reverse("investments:holdings")

    # Fetch fresh from database to ensure encryption roundtrip
    conn = BrokerConnection.objects.get(user=user, broker="zerodha")
    assert conn.encrypted_access_token == "super_secret_kite_access_token_xyz"
    assert conn.token_expires_at > timezone.now()


@pytest.mark.django_db
def test_holdings_view_shows_reconnect_prompt_when_token_expired(client):
    user = UserFactory()
    client.force_login(user)

    # Expired token
    BrokerConnectionFactory(
        user=user,
        token_expires_at=timezone.now() - timedelta(hours=5),
    )

    url = reverse("investments:holdings")
    response = client.get(url)

    assert response.status_code == 200
    assert response.context["needs_reconnect"] is True
    content = response.content.decode()
    assert "Broker Session Expired or Disconnected" in content
    assert reverse("investments:connect") in content


@pytest.mark.django_db
def test_holdings_view_displays_holdings_when_token_valid(client):
    user = UserFactory()
    client.force_login(user)

    connection = BrokerConnectionFactory(
        user=user,
        token_expires_at=timezone.now() + timedelta(hours=15),
    )
    HoldingFactory(
        user=user,
        broker_connection=connection,
        symbol="INFY",
        quantity=15,
        avg_price=1400,
        last_synced_price=1550,
    )

    url = reverse("investments:holdings")
    response = client.get(url)

    assert response.status_code == 200
    assert response.context["needs_reconnect"] is False
    assert len(response.context["holdings"]) == 1
    content = response.content.decode()
    assert "INFY" in content
    assert "1550" in content
