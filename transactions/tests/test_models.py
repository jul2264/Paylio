from datetime import date
from decimal import Decimal
import pytest
from django.db import IntegrityError, transaction
from accounts.tests.factories import UserFactory
from transactions.models import Category, FinancialAccount, Transaction, UserMerchantCategory
from transactions.tests.factories import (
    CategoryFactory,
    FinancialAccountFactory,
    TransactionFactory,
    UserMerchantCategoryFactory,
)


@pytest.mark.django_db
def test_category_unique_per_user():
    user_a = UserFactory()
    user_b = UserFactory()

    Category.objects.create(user=user_a, name="Food", kind=Category.EXPENSE)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Category.objects.create(user=user_a, name="Food", kind=Category.EXPENSE)

    cat_b = Category.objects.create(user=user_b, name="Food", kind=Category.EXPENSE)
    assert cat_b.pk is not None


@pytest.mark.django_db
def test_transaction_external_id_unique_per_account():
    user = UserFactory()
    account = FinancialAccountFactory(user=user)
    category = CategoryFactory(user=user)

    Transaction.objects.create(
        user=user,
        account=account,
        category=category,
        amount=Decimal("150.00"),
        date=date.today(),
        merchant="Store 1",
        external_id="TXN123",
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Transaction.objects.create(
                user=user,
                account=account,
                category=category,
                amount=Decimal("200.00"),
                date=date.today(),
                merchant="Store 2",
                external_id="TXN123",
            )

    # Partial unique condition: multiple transactions with external_id=None must both save successfully
    txn_none_1 = Transaction.objects.create(
        user=user,
        account=account,
        category=category,
        amount=Decimal("50.00"),
        date=date.today(),
        merchant="Cash 1",
        external_id=None,
    )
    txn_none_2 = Transaction.objects.create(
        user=user,
        account=account,
        category=category,
        amount=Decimal("75.00"),
        date=date.today(),
        merchant="Cash 2",
        external_id=None,
    )
    assert txn_none_1.pk is not None
    assert txn_none_2.pk is not None


@pytest.mark.django_db
def test_transaction_str():
    user = UserFactory()
    txn = TransactionFactory(user=user, merchant="Coffee Shop", amount=Decimal("250.50"))
    assert str(txn) == "Coffee Shop - 250.50"


@pytest.mark.django_db
def test_usermerchantcategory_unique_per_user_merchant():
    user_a = UserFactory()
    user_b = UserFactory()
    cat_a = CategoryFactory(user=user_a)
    cat_b = CategoryFactory(user=user_b)

    UserMerchantCategory.objects.create(
        user=user_a,
        merchant_normalized="swiggy",
        category=cat_a,
    )

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            UserMerchantCategory.objects.create(
                user=user_a,
                merchant_normalized="swiggy",
                category=cat_a,
            )

    umc_b = UserMerchantCategory.objects.create(
        user=user_b,
        merchant_normalized="swiggy",
        category=cat_b,
    )
    assert umc_b.pk is not None
