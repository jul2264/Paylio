import pytest
from django.db import connection
from accounts.tests.factories import UserFactory
from integrations.models import BankConsent


@pytest.mark.django_db
def test_encrypted_field_roundtrip():
    user = UserFactory()
    consent = BankConsent.objects.create(
        user=user,
        aa_provider="setu",
        consent_handle="consent-123",
        encrypted_metadata="secret-payload-123",
    )

    # Fetch fresh instance from the database
    fresh = BankConsent.objects.get(pk=consent.pk)
    assert fresh.encrypted_metadata == "secret-payload-123"


@pytest.mark.django_db
def test_encrypted_field_stores_ciphertext_not_plaintext():
    user = UserFactory()
    secret = "my-ultra-confidential-token-999"
    consent = BankConsent.objects.create(
        user=user,
        aa_provider="setu",
        consent_handle="consent-456",
        encrypted_metadata=secret,
    )

    with connection.cursor() as cur:
        cur.execute(
            "SELECT encrypted_metadata FROM integrations_bankconsent WHERE id=%s",
            [consent.pk],
        )
        raw_val = cur.fetchone()[0]

    # Verify that raw SQL value contains ciphertext and NOT plaintext
    assert secret not in raw_val
    assert len(raw_val) > len(secret)
