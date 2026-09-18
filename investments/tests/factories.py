from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
import factory
from accounts.tests.factories import UserFactory
from investments.models import BrokerConnection, Holding, PortfolioSnapshot


class BrokerConnectionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BrokerConnection

    user = factory.SubFactory(UserFactory)
    broker = "zerodha"
    encrypted_access_token = "dummy_access_token_secret"
    token_expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(hours=20))


class HoldingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Holding

    user = factory.SubFactory(UserFactory)
    broker_connection = factory.SubFactory(
        BrokerConnectionFactory,
        user=factory.SelfAttribute("..user"),
    )
    symbol = factory.Sequence(lambda n: f"SYM{n}")
    asset_type = Holding.EQUITY
    quantity = Decimal("10.0000")
    avg_price = Decimal("100.00")
    last_synced_price = Decimal("120.00")
    last_synced_at = factory.LazyFunction(timezone.now)


class PortfolioSnapshotFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PortfolioSnapshot

    user = factory.SubFactory(UserFactory)
    date = factory.LazyFunction(date.today)
    total_value = Decimal("50000.00")
