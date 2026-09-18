from django.conf import settings
from django.db import models
from transactions.models import Category


class Insight(models.Model):
    INFO, WARNING, CRITICAL = "INFO", "WARNING", "CRITICAL"
    SEVERITY_CHOICES = [(INFO, "Info"), (WARNING, "Warning"), (CRITICAL, "Critical")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rule_key = models.CharField(max_length=50)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
    period_start = models.DateField()
    period_end = models.DateField()
    summary = models.CharField(max_length=255)
    raw_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.severity}] {self.summary}"


class AdviceMessage(models.Model):
    insight = models.ForeignKey(Insight, on_delete=models.CASCADE, related_name="advice")
    body = models.TextField()
    model_used = models.CharField(max_length=50)
    user_feedback = models.CharField(max_length=15, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Advice for Insight #{self.insight_id}"
