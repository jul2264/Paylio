import pytest
from accounts.tests.factories import UserFactory
from transactions.categorization import (
    categorize,
    normalize_merchant,
    record_user_correction,
)
from transactions.models import UserMerchantCategory
from transactions.tests.factories import CategoryFactory, TransactionFactory


def test_normalize_merchant_strips_noise():
    raw = "SWIGGY* Bangalore #42!"
    normalized = normalize_merchant(raw)
    assert normalized == "swiggy bangalore 42"


@pytest.mark.django_db
def test_categorize_tier1_learned_mapping_takes_precedence():
    user = UserFactory()
    shopping = CategoryFactory(user=user, name="Shopping")
    UserMerchantCategory.objects.create(
        user=user,
        merchant_normalized="swiggy hsr",
        category=shopping,
    )

    # Merchant has "swiggy" which matches keyword rule, but learned mapping must win
    txn = TransactionFactory(user=user, merchant="SWIGGY HSR", category=None)
    categorize(txn)
    txn.refresh_from_db()

    assert txn.category == shopping


@pytest.mark.django_db
def test_categorize_tier2_keyword_match():
    user = UserFactory()
    txn = TransactionFactory(user=user, merchant="SWIGGY Koramangala", category=None)

    categorize(txn)
    txn.refresh_from_db()

    assert txn.category is not None
    assert txn.category.name == "Food & Dining"


@pytest.mark.django_db
def test_categorize_no_match_leaves_uncategorized():
    user = UserFactory()
    txn = TransactionFactory(user=user, merchant="XYZ RANDOM 123", category=None)

    categorize(txn)
    txn.refresh_from_db()

    assert txn.category is None


@pytest.mark.django_db
def test_record_user_correction_updates_transaction_and_learns():
    user = UserFactory()
    shopping = CategoryFactory(user=user, name="Shopping")
    dining = CategoryFactory(user=user, name="Food & Dining")
    txn = TransactionFactory(user=user, merchant="Swiggy Koramangala", category=None)

    # First correction: learn Shopping
    record_user_correction(txn, shopping)
    txn.refresh_from_db()
    assert txn.category == shopping
    assert UserMerchantCategory.objects.filter(
        user=user, merchant_normalized="swiggy koramangala", category=shopping
    ).exists()
    assert UserMerchantCategory.objects.filter(user=user).count() == 1

    # Second correction: update existing mapping in-place to Dining
    record_user_correction(txn, dining)
    txn.refresh_from_db()
    assert txn.category == dining
    assert UserMerchantCategory.objects.filter(
        user=user, merchant_normalized="swiggy koramangala", category=dining
    ).exists()
    assert UserMerchantCategory.objects.filter(user=user).count() == 1
