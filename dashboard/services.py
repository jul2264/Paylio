from decimal import Decimal
from django.db.models import Sum
from transactions.models import Transaction


def get_monthly_summary(user, year, month):
    """Aggregate monthly spending totals and category breakdown for a given user."""
    qs = Transaction.objects.filter(user=user, date__year=year, date__month=month)
    total_spent = (
        qs.filter(kind=Transaction.EXPENSE).aggregate(total=Sum("amount"))["total"]
        or Decimal("0")
    )
    total_income = (
        qs.filter(kind=Transaction.INCOME).aggregate(total=Sum("amount"))["total"]
        or Decimal("0")
    )
    by_category_raw = list(
        qs.filter(kind=Transaction.EXPENSE)
        .values("category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    by_category = [
        {
            "name": row["category__name"] or "Uncategorized",
            "category__name": row["category__name"] or "Uncategorized",
            "total": row["total"],
        }
        for row in by_category_raw
    ]
    return {
        "total_spent": total_spent,
        "total_income": total_income,
        "by_category": by_category,
    }
