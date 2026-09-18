from datetime import date
from dateutil.relativedelta import relativedelta
from django.db.models import Sum
from budgets.models import Budget
from transactions.models import Transaction
from .models import Insight


class BaseRule:
    key: str
    severity: str

    def evaluate(self, user, period_start, period_end):
        raise NotImplementedError


class BudgetOverspendRule(BaseRule):
    key = "budget_overspend"
    severity = Insight.WARNING

    def evaluate(self, user, period_start, period_end):
        insights = []
        for budget in Budget.objects.filter(user=user).select_related("category"):
            spent = Transaction.objects.filter(
                user=user, category=budget.category, date__range=(period_start, period_end)
            ).aggregate(total=Sum("amount"))["total"] or 0
            if spent > budget.monthly_limit:
                pct_over = round((float(spent) / float(budget.monthly_limit) - 1) * 100)
                insights.append(Insight.objects.create(
                    user=user,
                    rule_key=self.key,
                    severity=self.severity,
                    category=budget.category,
                    period_start=period_start,
                    period_end=period_end,
                    summary=f"{budget.category.name} spending is {pct_over}% over budget",
                    raw_data={"spent": float(spent), "limit": float(budget.monthly_limit), "pct_over": pct_over},
                ))
        return insights


class TrendIncreaseRule(BaseRule):
    key = "trend_increase"
    severity = Insight.INFO
    THRESHOLD_PCT = 30  # flag categories up >30% vs trailing 3-month average

    def evaluate(self, user, period_start, period_end):
        insights = []
        categories = Transaction.objects.filter(user=user).values_list("category", flat=True).distinct()

        for cat_id in categories:
            if cat_id is None:
                continue
            current = Transaction.objects.filter(
                user=user, category_id=cat_id, date__range=(period_start, period_end)
            ).aggregate(total=Sum("amount"))["total"] or 0

            trailing_totals = []
            for i in range(1, 4):
                m_start = (period_start - relativedelta(months=i)).replace(day=1)
                m_end = m_start.replace(day=28) + relativedelta(day=31)
                total = Transaction.objects.filter(
                    user=user, category_id=cat_id, date__range=(m_start, m_end)
                ).aggregate(total=Sum("amount"))["total"] or 0
                trailing_totals.append(float(total))

            avg = sum(trailing_totals) / len(trailing_totals) if trailing_totals else 0
            if avg > 0 and float(current) > avg * (1 + self.THRESHOLD_PCT / 100):
                pct_increase = round((float(current) / avg - 1) * 100)
                insights.append(Insight.objects.create(
                    user=user,
                    rule_key=self.key,
                    severity=self.severity,
                    category_id=cat_id,
                    period_start=period_start,
                    period_end=period_end,
                    summary=f"Spending up {pct_increase}% vs your 3-month average",
                    raw_data={"current": float(current), "trailing_avg": avg, "pct_increase": pct_increase},
                ))
        return insights


RULES = [BudgetOverspendRule(), TrendIncreaseRule()]


def run_rules_for_user(user, period_start, period_end):
    all_insights = []
    for rule in RULES:
        all_insights.extend(rule.evaluate(user, period_start, period_end))
    return all_insights
