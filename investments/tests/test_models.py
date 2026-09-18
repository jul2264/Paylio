from datetime import date
from decimal import Decimal
import pytest
from django.db import IntegrityError
from accounts.tests.factories import UserFactory
from investments.models import Holding, PortfolioSnapshot
from investments.tests.factories import BrokerConnectionFactory, HoldingFactory


@pytest.mark.django_db
def test_holding_unique_per_connection_and_symbol():
    connection = BrokerConnectionFactory()
    HoldingFactory(
        broker_connection=connection,
        user=connection.user,
        symbol="TCS",
    )

    with pytest.raises(IntegrityError):
        Holding.objects.create(
            user=connection.user,
            broker_connection=connection,
            symbol="TCS",
            quantity=Decimal("5.0"),
            avg_price=Decimal("3500.0"),
        )


@pytest.mark.django_db
def test_portfolio_snapshot_unique_per_user_and_date():
    user = UserFactory()
    today = date(2026, 9, 18)

    PortfolioSnapshot.objects.create(
        user=user,
        date=today,
        total_value=Decimal("150000.00"),
    )

    with pytest.raises(IntegrityError):
        PortfolioSnapshot.objects.create(
            user=user,
            date=today,
            total_value=Decimal("200000.00"),
        )
