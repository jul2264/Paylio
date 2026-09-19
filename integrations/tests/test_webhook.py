import hashlib
import hmac
import json
import pytest
from django.conf import settings
from django.test import Client
from accounts.tests.factories import UserFactory
from integrations.models import BankConsent


@pytest.mark.django_db
def test_setu_webhook_valid_signature_activates_consent():
    user = UserFactory()
    consent = BankConsent.objects.create(
        user=user,
        aa_provider="setu",
        consent_handle="consent-uuid-12345",
        status=BankConsent.PENDING,
    )

    client = Client()
    payload = json.dumps({"consentId": "consent-uuid-12345", "status": "ACTIVE"}).encode("utf-8")
    secret = getattr(settings, "SETU_WEBHOOK_SECRET", "test_setu_webhook_secret")
    signature = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    response = client.post(
        "/integrations/setu/webhook/",
        data=payload,
        content_type="application/json",
        HTTP_X_SETU_SIGNATURE=signature,
    )

    assert response.status_code == 204
    consent.refresh_from_db()
    assert consent.status == BankConsent.ACTIVE


@pytest.mark.django_db
def test_setu_webhook_invalid_signature_returns_400():
    client = Client()
    payload = json.dumps({"consentId": "consent-uuid-12345", "status": "ACTIVE"}).encode("utf-8")

    response = client.post(
        "/integrations/setu/webhook/",
        data=payload,
        content_type="application/json",
        HTTP_X_SETU_SIGNATURE="invalid_fake_signature",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_setu_webhook_missing_signature_returns_400():
    client = Client()
    payload = json.dumps({"consentId": "consent-uuid-12345", "status": "ACTIVE"}).encode("utf-8")

    response = client.post(
        "/integrations/setu/webhook/",
        data=payload,
        content_type="application/json",
    )

    assert response.status_code == 400
