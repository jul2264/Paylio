from datetime import date
from decimal import Decimal
import factory
from transactions.models import Category, FinancialAccount, Transaction, UserMerchantCategory


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Category {n}")
    kind = Category.EXPENSE


class FinancialAccountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FinancialAccount

    name = factory.Sequence(lambda n: f"Account {n}")
    account_type = FinancialAccount.CHECKING
    currency = "INR"


class TransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Transaction

    account = factory.SubFactory(
        FinancialAccountFactory,
        user=factory.SelfAttribute("..user"),
    )
    category = factory.SubFactory(
        CategoryFactory,
        user=factory.SelfAttribute("..user"),
    )
    amount = Decimal("100.00")
    date = factory.LazyFunction(date.today)
    merchant = factory.Sequence(lambda n: f"Merchant {n}")
    description = ""
    source = Transaction.MANUAL
    external_id = None
    is_recurring = False


class UserMerchantCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserMerchantCategory

    merchant_normalized = factory.Sequence(lambda n: f"merchant_{n}")
    category = factory.SubFactory(
        CategoryFactory,
        user=factory.SelfAttribute("..user"),
    )
