from django.contrib import admin
from transactions.models import Category, FinancialAccount, Transaction, UserMerchantCategory


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "user", "parent")
    list_filter = ("kind", "user")
    search_fields = ("name", "user__username")


@admin.register(FinancialAccount)
class FinancialAccountAdmin(admin.ModelAdmin):
    list_display = ("name", "account_type", "currency", "user")
    list_filter = ("account_type", "user")
    search_fields = ("name", "user__username")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("date", "merchant", "amount", "category", "account", "source", "user")
    list_filter = ("source", "category", "account", "user")
    search_fields = ("merchant", "description", "external_id", "user__username")
    date_hierarchy = "date"


@admin.register(UserMerchantCategory)
class UserMerchantCategoryAdmin(admin.ModelAdmin):
    list_display = ("merchant_normalized", "category", "user")
    list_filter = ("category", "user")
    search_fields = ("merchant_normalized", "user__username")
