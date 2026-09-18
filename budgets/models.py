from django.conf import settings
from django.db import models
from transactions.models import Category


class Budget(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    monthly_limit = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = ("user", "category")

    def __str__(self):
        return f"{self.category} — ₹{self.monthly_limit}/mo"
