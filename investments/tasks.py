from datetime import date
from celery import shared_task
from django.utils import timezone
from integrations.brokers.kite import fetch_holdings
from .models import BrokerConnection, Holding, PortfolioSnapshot


@shared_task(acks_late=True, retry_backoff=True, max_retries=3)
def sync_holdings_for_user(user_id):
    connection = BrokerConnection.objects.filter(user_id=user_id, broker="zerodha").first()
    if connection is None or connection.token_expires_at < timezone.now():
        return
    raw_holdings = fetch_holdings(connection.encrypted_access_token)
    total_value = 0
    for h in raw_holdings:
        Holding.objects.update_or_create(
            broker_connection=connection,
            symbol=h["tradingsymbol"],
            defaults={
                "user_id": user_id,
                "asset_type": Holding.EQUITY,
                "quantity": h["quantity"],
                "avg_price": h["average_price"],
                "last_synced_price": h["last_price"],
                "last_synced_at": timezone.now(),
            },
        )
        total_value += h["quantity"] * h["last_price"]
    PortfolioSnapshot.objects.update_or_create(
        user_id=user_id,
        date=date.today(),
        defaults={"total_value": total_value},
    )


@shared_task
def sync_all_holdings():
    for connection in BrokerConnection.objects.filter(broker="zerodha"):
        sync_holdings_for_user.apply_async(
            args=[connection.user_id], countdown=connection.user_id % 300
        )
