from django.conf import settings
from django.db import models
from integrations.fields import EncryptedTextField


class BrokerConnection(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    broker = models.CharField(max_length=30, default="zerodha")
    encrypted_access_token = EncryptedTextField()
    token_expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.broker}"


class Holding(models.Model):
    EQUITY, MUTUAL_FUND, BOND = "EQUITY", "MUTUAL_FUND", "BOND"
    ASSET_CHOICES = [(EQUITY, "Equity"), (MUTUAL_FUND, "Mutual Fund"), (BOND, "Bond")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    broker_connection = models.ForeignKey(BrokerConnection, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=50)
    asset_type = models.CharField(max_length=15, choices=ASSET_CHOICES, default=EQUITY)
    quantity = models.DecimalField(max_digits=12, decimal_places=4)
    avg_price = models.DecimalField(max_digits=12, decimal_places=2)
    last_synced_price = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    last_synced_at = models.DateTimeField(null=True)

    class Meta:
        unique_together = ("broker_connection", "symbol")

    def __str__(self):
        return f"{self.symbol} ({self.quantity} @ {self.avg_price})"


class PortfolioSnapshot(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField()
    total_value = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        unique_together = ("user", "date")

    def __str__(self):
        return f"{self.user.username} - {self.date}: {self.total_value}"
