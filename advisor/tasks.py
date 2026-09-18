from datetime import date
from celery import shared_task
from django.contrib.auth import get_user_model
from .ai import categorize_via_llm, generate_advice
from .rules import run_rules_for_user


@shared_task(acks_late=True, retry_backoff=True, max_retries=3)
def run_daily_insights():
    today = date.today()
    for user in get_user_model().objects.filter(is_active=True):
        for insight in run_rules_for_user(user, today.replace(day=1), today):
            try:
                generate_advice(insight)
            except Exception:
                pass


@shared_task(acks_late=True, retry_backoff=True, max_retries=3)
def categorize_with_llm(transaction_id):
    from transactions.models import Transaction

    txn = Transaction.objects.select_related("user").get(id=transaction_id)
    categorize_via_llm(txn)
