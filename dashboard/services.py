from decimal import Decimal
from django.db.models import Sum
from transactions.models import Transaction


def get_monthly_summary(user, year, month):
    """Aggregate monthly spending totals and category breakdown for a given user."""
    qs = Transaction.objects.filter(user=user, date__year=year, date__month=month)
    total = qs.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    by_category = list(
        qs.values("category__name").annotate(total=Sum("amount")).order_by("-total")
    )
    return {"total_spent": total, "by_category": by_category}
