from datetime import timedelta
from django.utils import timezone
import pytest
from accounts.tests.factories import UserFactory
from integrations.models import BankConsent


@pytest.mark.django_db
def test_bank_consent_creation_defaults():
    user = UserFactory(username="consent_user")
    consent = BankConsent.objects.create(
        user=user,
        consent_handle="handle-xyz-789",
    )

    assert consent.user == user
    assert consent.aa_provider == "setu"
    assert consent.status == BankConsent.PENDING
    assert consent.consent_handle == "handle-xyz-789"
    assert consent.encrypted_metadata == ""
    assert consent.created_at is not None
    assert str(consent) == "consent_user - setu (Pending)"


@pytest.mark.django_db
def test_bank_consent_status_transitions():
    user = UserFactory()
    consent = BankConsent.objects.create(
        user=user,
        consent_handle="handle-lifecycle",
        status=BankConsent.PENDING,
    )

    # Transition to ACTIVE with expiration date
    future_date = timezone.now() + timedelta(days=365)
    consent.status = BankConsent.ACTIVE
    consent.valid_till = future_date
    consent.save()

    refreshed = BankConsent.objects.get(pk=consent.pk)
    assert refreshed.status == BankConsent.ACTIVE
    assert refreshed.valid_till == future_date
    assert str(refreshed) == f"{user.username} - setu (Active)"

    # Transition to REVOKED
    consent.status = BankConsent.REVOKED
    consent.save()

    refreshed = BankConsent.objects.get(pk=consent.pk)
    assert refreshed.status == BankConsent.REVOKED
    assert str(refreshed) == f"{user.username} - setu (Revoked)"
