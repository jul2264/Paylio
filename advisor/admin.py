from django.contrib import admin
from .models import AdviceMessage, Insight


@admin.register(Insight)
class InsightAdmin(admin.ModelAdmin):
    list_display = ("summary", "user", "rule_key", "severity", "period_start", "period_end", "created_at")
    list_filter = ("severity", "rule_key", "created_at")
    search_fields = ("summary", "user__username")


@admin.register(AdviceMessage)
class AdviceMessageAdmin(admin.ModelAdmin):
    list_display = ("insight", "model_used", "user_feedback", "created_at")
    list_filter = ("model_used", "user_feedback", "created_at")
    search_fields = ("body", "insight__summary")
