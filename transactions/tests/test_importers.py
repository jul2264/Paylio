import io
from decimal import Decimal
import pytest
from accounts.tests.factories import UserFactory
from transactions.importers import import_csv
from transactions.models import Transaction
from transactions.tests.factories import CategoryFactory, FinancialAccountFactory


@pytest.mark.django_db
def test_import_csv_creates_and_categorizes_transactions():
    user = UserFactory()
    account = FinancialAccountFactory(user=user)
    dining_cat = CategoryFactory(user=user, name="Food & Dining")

    csv_content = (
        "Date,Amount,Narration,Reference No\n"
        "2026-09-15,450.50,SWIGGY Koramangala,REF12345\n"
    )
    file = io.StringIO(csv_content)

    created_count, affected_months = import_csv(user, account, file)

    assert created_count == 1
    assert affected_months == {(2026, 9)}

    txn = Transaction.objects.get(external_id="REF12345")
    assert txn.user == user
    assert txn.account == account
    assert txn.amount == Decimal("450.50")
    assert txn.merchant == "SWIGGY Koramangala"
    assert txn.source == Transaction.BANK_SYNC
    assert txn.category == dining_cat


@pytest.mark.django_db
def test_import_csv_is_idempotent_on_rerun():
    user = UserFactory()
    account = FinancialAccountFactory(user=user)
    CategoryFactory(user=user, name="Dining & Delivery")

    csv_content = (
        "Date,Amount,Narration,Reference No\n"
        "2026-09-15,450.50,SWIGGY Koramangala,REF12345\n"
    )

    file1 = io.StringIO(csv_content)
    created_count1, _ = import_csv(user, account, file1)
    assert created_count1 == 1
    assert Transaction.objects.filter(account=account).count() == 1

    file2 = io.StringIO(csv_content)
    created_count2, _ = import_csv(user, account, file2)
    assert created_count2 == 0
    assert Transaction.objects.filter(account=account).count() == 1


@pytest.mark.django_db
def test_import_csv_falls_back_to_row_index_when_reference_no_missing():
    user = UserFactory()
    account = FinancialAccountFactory(user=user)
    CategoryFactory(user=user, name="Dining & Delivery")

    csv_content = (
        "Date,Amount,Narration,Reference No\n"
        "2026-09-15,120.00,SWIGGY Koramangala,\n"
    )
    file = io.StringIO(csv_content)

    created_count, _ = import_csv(user, account, file)
    assert created_count == 1

    txn = Transaction.objects.get(account=account)
    assert txn.external_id == "0"


@pytest.mark.django_db
def test_import_csv_returns_all_affected_months():
    user = UserFactory()
    account = FinancialAccountFactory(user=user)
    CategoryFactory(user=user, name="Food & Dining")
    CategoryFactory(user=user, name="Transport")

    csv_content = (
        "Date,Amount,Narration,Reference No\n"
        "2026-08-10,250.00,Uber Ride,REF_AUG\n"
        "2026-09-12,450.00,SWIGGY,REF_SEP\n"
        "2026-10-01,150.00,Uber,REF_OCT\n"
    )
    file = io.StringIO(csv_content)

    created_count, affected_months = import_csv(user, account, file)
    assert created_count == 3
    assert affected_months == {(2026, 8), (2026, 9), (2026, 10)}
