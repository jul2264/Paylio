from unittest.mock import patch
import pytest
from rates.models import MetalRateSnapshot
from rates.tasks import refresh_metal_rates


@pytest.mark.django_db
def test_refresh_metal_rates_creates_a_snapshot_per_metal():
    fake_prices = {
        "GOLD": 7200.50,
        "SILVER": 88.25,
        "PLATINUM": 3150.00,
    }

    def fake_fetcher(metal):
        return fake_prices[metal]

    with patch("rates.tasks.fetch_price_per_gram_inr", side_effect=fake_fetcher) as mock_fetch:
        refresh_metal_rates()
        assert mock_fetch.call_count == 3

    assert MetalRateSnapshot.objects.count() == 3

    gold_snap = MetalRateSnapshot.objects.get(metal="GOLD")
    assert float(gold_snap.price_per_gram_999) == 7200.50

    silver_snap = MetalRateSnapshot.objects.get(metal="SILVER")
    assert float(silver_snap.price_per_gram_999) == 88.25

    plat_snap = MetalRateSnapshot.objects.get(metal="PLATINUM")
    assert float(plat_snap.price_per_gram_999) == 3150.00


@pytest.mark.django_db
def test_refresh_metal_rates_prunes_older_than_7_days():
    from datetime import timedelta
    from decimal import Decimal
    from django.utils import timezone

    old_snap = MetalRateSnapshot.objects.create(
        metal="GOLD",
        price_per_gram_999=Decimal("7000.00"),
    )
    MetalRateSnapshot.objects.filter(id=old_snap.id).update(
        fetched_at=timezone.now() - timedelta(days=8)
    )

    with patch("rates.tasks.fetch_price_per_gram_inr", return_value=7200.00):
        refresh_metal_rates()

    assert not MetalRateSnapshot.objects.filter(id=old_snap.id).exists()
    assert MetalRateSnapshot.objects.count() == 3
