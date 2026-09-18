from django.contrib import admin
from budgets.models import Budget


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("category", "monthly_limit", "user")
    list_filter = ("user",)
    search_fields = ("category__name", "user__username")
