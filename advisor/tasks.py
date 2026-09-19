from datetime import date
from celery import shared_task
from django.contrib.auth import get_user_model
from .rules import run_rules_for_user


@shared_task(acks_late=True, retry_backoff=True, max_retries=3)
def run_daily_insights():
    from .ai import generate_advice

    today = date.today()
    for user in get_user_model().objects.filter(is_active=True):
        for insight in run_rules_for_user(user, today.replace(day=1), today):
            try:
                generate_advice(insight)
            except Exception:
                pass
            if getattr(insight, "severity", None) == "CRITICAL":
                try:
                    from api.notifications import send_push_notification_for_insight
                    send_push_notification_for_insight(user, insight)
                except Exception:
                    pass


@shared_task(acks_late=True, retry_backoff=True, max_retries=3)
def categorize_with_llm(transaction_id):
    from .ai import categorize_via_llm
    from transactions.models import Transaction

    txn = Transaction.objects.select_related("user").get(id=transaction_id)
    categorize_via_llm(txn)


@shared_task(acks_late=True, retry_backoff=True, max_retries=3)
def purge_old_insights():
    """Purge insights older than 90 days to prevent unbounded database growth."""
    from datetime import timedelta
    from django.utils import timezone
    from .models import Insight

    cutoff = timezone.now() - timedelta(days=90)
    deleted_count, _ = Insight.objects.filter(created_at__lt=cutoff).delete()
    return deleted_count


@shared_task(acks_late=True, retry_backoff=True, max_retries=3)
def detect_recurring_for_all_users():
    """Run recurring transaction heuristic detection for all active users."""
    from transactions.recurring import detect_recurring_transactions

    total_flagged = 0
    for user in get_user_model().objects.filter(is_active=True):
        total_flagged += detect_recurring_transactions(user)
    return total_flagged
