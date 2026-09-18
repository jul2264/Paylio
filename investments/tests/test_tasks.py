from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch
from django.utils import timezone
import pytest
from accounts.tests.factories import UserFactory
from investments.models import Holding, PortfolioSnapshot
from investments.tasks import sync_all_holdings, sync_holdings_for_user
from investments.tests.factories import BrokerConnectionFactory


@pytest.mark.django_db
def test_sync_holdings_creates_holdings_and_snapshot():
    user = UserFactory()
    connection = BrokerConnectionFactory(
        user=user,
        token_expires_at=timezone.now() + timedelta(hours=10),
    )

    fake_holdings = [
        {"tradingsymbol": "INFY", "quantity": 10, "average_price": 1500.0, "last_price": 1600.0},
        {"tradingsymbol": "RELIANCE", "quantity": 5, "average_price": 2500.0, "last_price": 2700.0},
    ]

    with patch("investments.tasks.fetch_holdings", return_value=fake_holdings) as mock_fetch:
        sync_holdings_for_user(user.id)
        mock_fetch.assert_called_once_with(connection.encrypted_access_token)

    # Check holdings saved
    assert Holding.objects.filter(broker_connection=connection).count() == 2
    infy = Holding.objects.get(broker_connection=connection, symbol="INFY")
    assert infy.quantity == Decimal("10")
    assert infy.avg_price == Decimal("1500.0")
    assert infy.last_synced_price == Decimal("1600.0")

    # Check portfolio snapshot
    # 10 * 1600 + 5 * 2700 = 16000 + 13500 = 29500
    snapshot = PortfolioSnapshot.objects.get(user=user, date=date.today())
    assert snapshot.total_value == Decimal("29500.00")


@pytest.mark.django_db
def test_sync_holdings_skips_expired_connection():
    user = UserFactory()
    BrokerConnectionFactory(
        user=user,
        token_expires_at=timezone.now() - timedelta(hours=2),
    )

    with patch("investments.tasks.fetch_holdings") as mock_fetch:
        sync_holdings_for_user(user.id)
        mock_fetch.assert_not_called()

    assert Holding.objects.count() == 0
    assert PortfolioSnapshot.objects.count() == 0


@pytest.mark.django_db
def test_sync_all_holdings_staggers_each_user():
    user1 = UserFactory()
    user2 = UserFactory()
    BrokerConnectionFactory(user=user1)
    BrokerConnectionFactory(user=user2)

    with patch("investments.tasks.sync_holdings_for_user.apply_async") as mock_apply:
        sync_all_holdings()

        assert mock_apply.call_count == 2
        calls = mock_apply.call_args_list

        expected_countdowns = {user1.id: user1.id % 300, user2.id: user2.id % 300}
        for call in calls:
            uid = call.kwargs["args"][0]
            assert call.kwargs["countdown"] == expected_countdowns[uid]
