import hashlib
import hmac
import json
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from .models import BankConsent


@method_decorator(csrf_exempt, name="dispatch")
class SetuConsentWebhook(View):
    """
    Webhook endpoint for Setu Account Aggregator consent updates.
    Verifies HMAC-SHA256 signature in X-Setu-Signature header.
    """

    def post(self, request, *args, **kwargs):
        signature = request.headers.get("x-setu-signature") or request.META.get("HTTP_X_SETU_SIGNATURE")
        secret = getattr(settings, "SETU_WEBHOOK_SECRET", "")

        if not signature or not secret:
            return HttpResponseBadRequest("Missing signature or webhook secret")

        expected = hmac.new(
            secret.encode("utf-8"),
            request.body,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected):
            return HttpResponseBadRequest("Invalid signature")

        try:
            payload = json.loads(request.body.decode("utf-8"))
        except Exception:
            return HttpResponseBadRequest("Invalid JSON body")

        consent_handle = payload.get("consentId") or payload.get("consent_handle") or payload.get("id")
        status_val = payload.get("status")

        if consent_handle and status_val:
            status_map = {
                "ACTIVE": BankConsent.ACTIVE,
                "REVOKED": BankConsent.REVOKED,
                "EXPIRED": BankConsent.EXPIRED,
                "PENDING": BankConsent.PENDING,
            }
            mapped_status = status_map.get(status_val.upper())
            if mapped_status:
                BankConsent.objects.filter(consent_handle=consent_handle).update(status=mapped_status)

        return HttpResponse(status=204)
