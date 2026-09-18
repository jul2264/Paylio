import json
from datetime import date
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import render
from dashboard.services import get_monthly_summary


@login_required
def dashboard(request):
    today = date.today()
    cache_key = f"dashboard:{request.user.id}:{today.year}-{today.month}"
    summary = cache.get(cache_key)
    if summary is None:
        summary = get_monthly_summary(request.user, today.year, today.month)
        cache.set(cache_key, summary, timeout=300)

    chart_labels = [row["category__name"] or "Uncategorized" for row in summary["by_category"]]
    chart_values = [float(row["total"]) for row in summary["by_category"]]

    return render(
        request,
        "dashboard/dashboard.html",
        {
            "total_spent": summary["total_spent"],
            "by_category": summary["by_category"],
            "current_month": today.strftime("%B %Y"),
            "chart_labels": json.dumps(chart_labels),
            "chart_values": json.dumps(chart_values),
        },
    )
