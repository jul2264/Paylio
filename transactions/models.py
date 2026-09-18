from django.conf import settings
from django.db import models


class Category(models.Model):
    INCOME, EXPENSE = "INCOME", "EXPENSE"
    KIND_CHOICES = [(INCOME, "Income"), (EXPENSE, "Expense")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL)
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default=EXPENSE)

    class Meta:
        verbose_name_plural = "categories"
        unique_together = ("user", "name")

    def __str__(self):
        return self.name


class FinancialAccount(models.Model):
    CHECKING, SAVINGS, CREDIT_CARD, CASH = "CHECKING", "SAVINGS", "CREDIT_CARD", "CASH"
    TYPE_CHOICES = [
        (CHECKING, "Checking"),
        (SAVINGS, "Savings"),
        (CREDIT_CARD, "Credit Card"),
        (CASH, "Cash"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    account_type = models.CharField(max_length=15, choices=TYPE_CHOICES)
    currency = models.CharField(max_length=3, default="INR")

    def __str__(self):
        return self.name


class Transaction(models.Model):
    MANUAL, BANK_SYNC = "MANUAL", "BANK_SYNC"
    SOURCE_CHOICES = [(MANUAL, "Manual"), (BANK_SYNC, "Bank Sync")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    account = models.ForeignKey(FinancialAccount, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    merchant = models.CharField(max_length=200, blank=True)
    description = models.CharField(max_length=255, blank=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=MANUAL)
    external_id = models.CharField(max_length=200, null=True, blank=True)
    is_recurring = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "date"]),
            models.Index(fields=["user", "category", "date"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["account", "external_id"],
                name="unique_external_txn_per_account",
                condition=models.Q(external_id__isnull=False),
            )
        ]

    def __str__(self):
        return f"{self.merchant} - {self.amount}"


class UserMerchantCategory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    merchant_normalized = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "user merchant categories"
        unique_together = ("user", "merchant_normalized")

    def __str__(self):
        return f"{self.merchant_normalized} -> {self.category.name}"
