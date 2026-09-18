from django.db import models


class MetalRateSnapshot(models.Model):
    GOLD, SILVER, PLATINUM = "GOLD", "SILVER", "PLATINUM"
    METAL_CHOICES = [(GOLD, "Gold"), (SILVER, "Silver"), (PLATINUM, "Platinum")]

    metal = models.CharField(max_length=10, choices=METAL_CHOICES)
    price_per_gram_999 = models.DecimalField(max_digits=10, decimal_places=2)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["metal", "-fetched_at"])]

    def __str__(self):
        return f"{self.get_metal_display()} - ₹{self.price_per_gram_999}/g ({self.fetched_at})"
