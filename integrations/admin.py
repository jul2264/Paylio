from django.contrib import admin
from .models import BankConsent


@admin.register(BankConsent)
class BankConsentAdmin(admin.ModelAdmin):
    list_display = ("user", "aa_provider", "status", "valid_till", "created_at")
    list_filter = ("status", "aa_provider")
    search_fields = ("user__username", "consent_handle")
