from datetime import date
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import render
from .services import get_budget_progress


@login_required
def progress_partial(request):
    today = date.today()
    cache_key = f"budget_progress:{request.user.id}:{today.year}-{today.month}"
    rows = cache.get(cache_key)
    if rows is None:
        rows = get_budget_progress(request.user, today.year, today.month)
        cache.set(cache_key, rows, timeout=300)
    return render(request, "partials/_budget_progress.html", {"rows": rows})
