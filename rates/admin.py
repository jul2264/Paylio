from django.contrib import admin
from .models import MetalRateSnapshot


@admin.register(MetalRateSnapshot)
class MetalRateSnapshotAdmin(admin.ModelAdmin):
    list_display = ("metal", "price_per_gram_999", "fetched_at")
    list_filter = ("metal", "fetched_at")
    search_fields = ("metal",)
