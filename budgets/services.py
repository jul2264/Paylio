from django.db.models import Sum
from .models import Budget
from transactions.models import Transaction


def get_budget_progress(user, year, month):
    rows = []
    for budget in Budget.objects.filter(user=user).select_related("category"):
        spent = Transaction.objects.filter(
            user=user, category=budget.category, date__year=year, date__month=month
        ).aggregate(total=Sum("amount"))["total"] or 0
        rows.append({
            "budget": budget,
            "spent": spent,
            "pct": min(int((spent / budget.monthly_limit) * 100), 100) if budget.monthly_limit else 0,
            "over": spent > budget.monthly_limit,
        })
    return rows
