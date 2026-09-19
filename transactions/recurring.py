from collections import defaultdict
from decimal import Decimal
from transactions.categorization import normalize_merchant
from transactions.models import Transaction


def detect_recurring_transactions(user) -> int:
    """
    Detect recurring transactions for a user:
    Finds merchants with transactions across at least 3 distinct calendar months
    where amounts are relatively consistent (within 15% of mean).
    Sets is_recurring=True on matching transactions.
    Returns the count of newly flagged transactions.
    """
    txns = Transaction.objects.filter(user=user).order_by("date")
    by_merchant = defaultdict(list)
    for txn in txns:
        norm = normalize_merchant(txn.merchant)
        if norm:
            by_merchant[norm].append(txn)

    flagged_count = 0
    for merchant_norm, merchant_txns in by_merchant.items():
        months = sorted(list({(t.date.year, t.date.month) for t in merchant_txns}))
        if len(months) < 3:
            continue

        # Check for 3 consecutive months
        has_consecutive_3 = False
        for i in range(len(months) - 2):
            y1, m1 = months[i]
            y2, m2 = months[i + 1]
            y3, m3 = months[i + 2]
            if (y2 * 12 + m2 == y1 * 12 + m1 + 1) and (y3 * 12 + m3 == y2 * 12 + m2 + 1):
                has_consecutive_3 = True
                break

        if not has_consecutive_3:
            continue

        # Check amount variance: within 15% of average
        amounts = [t.amount for t in merchant_txns]
        avg_amount = sum(amounts) / Decimal(len(amounts))
        if avg_amount == Decimal("0"):
            continue

        consistent = all(abs(amt - avg_amount) / avg_amount <= Decimal("0.15") for amt in amounts)
        if consistent:
            for t in merchant_txns:
                if not t.is_recurring:
                    t.is_recurring = True
                    t.save(update_fields=["is_recurring"])
                    flagged_count += 1

    return flagged_count
