import pandas as pd
from .categorization import categorize
from .models import FinancialAccount, Transaction


def import_csv(user, account: FinancialAccount, file):
    df = pd.read_csv(file)
    created_count = 0
    affected_months = set()
    for _, row in df.iterrows():
        ref_val = row.get("Reference No")
        external_id = str(ref_val) if pd.notna(ref_val) and str(ref_val).strip() != "" else str(row.name)

        txn, created = Transaction.objects.get_or_create(
            account=account,
            external_id=external_id,
            defaults={
                "user": user,
                "amount": abs(row["Amount"]),
                "date": pd.to_datetime(row["Date"]).date(),
                "merchant": str(row.get("Narration", ""))[:200],
                "source": Transaction.BANK_SYNC,
            },
        )
        if created:
            created_count += 1
            affected_months.add((txn.date.year, txn.date.month))
            if txn.category is None:
                categorize(txn)
    return created_count, affected_months
