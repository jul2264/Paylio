from decimal import Decimal
from django.urls import reverse
import pytest
from accounts.tests.factories import UserFactory
from rates.models import MetalRateSnapshot


@pytest.mark.django_db
def test_rates_widget_requires_login(client):
    url = reverse("rates:widget")
    response = client.get(url)
    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_rates_widget_computes_all_purities_from_latest_snapshot(client):
    user = UserFactory()
    client.force_login(user)

    MetalRateSnapshot.objects.create(metal="GOLD", price_per_gram_999=Decimal("6000.00"))
    MetalRateSnapshot.objects.create(metal="SILVER", price_per_gram_999=Decimal("80.00"))
    MetalRateSnapshot.objects.create(metal="PLATINUM", price_per_gram_999=Decimal("3000.00"))

    url = reverse("rates:widget")
    response = client.get(url)

    assert response.status_code == 200
    content = response.content.decode()

    # Gold purities
    assert "24K" in content
    assert "6000" in content
    assert "22K" in content
    assert "5500" in content
    assert "18K" in content
    assert "4500" in content

    # Silver purities
    assert "999 Fine" in content
    assert "958 Britannia" in content
    assert "925 Sterling" in content

    # Platinum purities
    assert "999" in content
    assert "950" in content
    assert "2850" in content


@pytest.mark.django_db
def test_rates_widget_handles_no_data_without_crashing(client):
    user = UserFactory()
    client.force_login(user)

    url = reverse("rates:widget")
    response = client.get(url)

    assert response.status_code == 200
    content = response.content.decode()
    assert "No precious metal rates recorded yet" in content
