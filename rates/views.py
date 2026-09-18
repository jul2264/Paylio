from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import MetalRateSnapshot
from .purity import GOLD_PURITIES, PLATINUM_PURITIES, SILVER_PURITIES, compute_purity_rates


@login_required
def rates_widget(request):
    context = {}
    for metal, table, key in [
        ("GOLD", GOLD_PURITIES, "gold"),
        ("SILVER", SILVER_PURITIES, "silver"),
        ("PLATINUM", PLATINUM_PURITIES, "platinum"),
    ]:
        latest = MetalRateSnapshot.objects.filter(metal=metal).order_by("-fetched_at").first()
        context[key] = compute_purity_rates(float(latest.price_per_gram_999), table) if latest else {}

    latest_snapshot = MetalRateSnapshot.objects.order_by("-fetched_at").first()
    context["last_updated"] = latest_snapshot.fetched_at if latest_snapshot else None
    return render(request, "partials/_metal_rates.html", context)
