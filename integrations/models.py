from django.conf import settings
from django.db import models
from .fields import EncryptedTextField


class BankConsent(models.Model):
    PENDING, ACTIVE, REVOKED, EXPIRED = "PENDING", "ACTIVE", "REVOKED", "EXPIRED"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (ACTIVE, "Active"),
        (REVOKED, "Revoked"),
        (EXPIRED, "Expired"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    aa_provider = models.CharField(max_length=30, default="setu")
    consent_handle = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    valid_till = models.DateTimeField(null=True, blank=True)
    encrypted_metadata = EncryptedTextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.aa_provider} ({self.status})"
