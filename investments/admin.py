from django.contrib import admin
from .models import BrokerConnection, Holding, PortfolioSnapshot


@admin.register(BrokerConnection)
class BrokerConnectionAdmin(admin.ModelAdmin):
    list_display = ("user", "broker", "token_expires_at", "created_at")
    list_filter = ("broker",)
    search_fields = ("user__username",)


@admin.register(Holding)
class HoldingAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "symbol",
        "asset_type",
        "quantity",
        "avg_price",
        "last_synced_price",
        "last_synced_at",
    )
    list_filter = ("asset_type",)
    search_fields = ("user__username", "symbol")


@admin.register(PortfolioSnapshot)
class PortfolioSnapshotAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "total_value")
    list_filter = ("date",)
    search_fields = ("user__username",)
