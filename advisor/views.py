from datetime import date
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import render
from .ai import generate_advice
from .models import Insight
from .rules import run_rules_for_user


@login_required
def feed_partial(request):
    insights = Insight.objects.filter(user=request.user).prefetch_related("advice").order_by("-created_at")[:10]
    return render(request, "partials/_advisor_feed.html", {"insights": insights})


@login_required
def refresh_insights(request):
    rate_key = f"advisor_refresh_lock:{request.user.id}"
    if not cache.add(rate_key, 1, timeout=300):
        return feed_partial(request)

    today = date.today()
    period_start = today.replace(day=1)
    new_insights = run_rules_for_user(request.user, period_start, today)
    for insight in new_insights:
        try:
            generate_advice(insight)
        except Exception:
            pass
    return feed_partial(request)
