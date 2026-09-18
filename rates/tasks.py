from celery import shared_task
from .fetcher import fetch_price_per_gram_inr
from .models import MetalRateSnapshot


@shared_task(acks_late=True, retry_backoff=True, max_retries=3)
def refresh_metal_rates():
    for metal in ["GOLD", "SILVER", "PLATINUM"]:
        MetalRateSnapshot.objects.create(
            metal=metal, price_per_gram_999=fetch_price_per_gram_inr(metal)
        )
