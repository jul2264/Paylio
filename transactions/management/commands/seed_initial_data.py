from decimal import Decimal
from django.core.management.base import BaseCommand
from accounts.models import User
from budgets.models import Budget
from transactions.models import Category, FinancialAccount


class Command(BaseCommand):
    help = "Seed initial categories, financial account, and budgets for superuser admin."

    def handle(self, *args, **options):
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            self.stdout.write(self.style.ERROR("No superuser found. Please create one first."))
            return

        categories_data = [
            ("Food & Dining", Category.EXPENSE),
            ("Transport", Category.EXPENSE),
            ("Shopping", Category.EXPENSE),
            ("Subscriptions", Category.EXPENSE),
            ("Utilities", Category.EXPENSE),
            ("Salary", Category.INCOME),
        ]

        created_cats = 0
        categories_by_name = {}
        for name, kind in categories_data:
            cat, created = Category.objects.get_or_create(
                user=user,
                name=name,
                defaults={"kind": kind},
            )
            categories_by_name[name] = cat
            if created:
                created_cats += 1

        account, acct_created = FinancialAccount.objects.get_or_create(
            user=user,
            name="Primary Checking",
            defaults={
                "account_type": FinancialAccount.CHECKING,
                "currency": "INR",
            },
        )

        budgets_data = [
            ("Food & Dining", Decimal("8000.00")),
            ("Transport", Decimal("3000.00")),
            ("Shopping", Decimal("5000.00")),
        ]

        created_budgets = 0
        for cat_name, limit in budgets_data:
            category = categories_by_name.get(cat_name)
            if category:
                budget, b_created = Budget.objects.get_or_create(
                    user=user,
                    category=category,
                    defaults={"monthly_limit": limit},
                )
                if b_created:
                    created_budgets += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded: {created_cats} new categories, primary account '{account.name}' (created={acct_created}), {created_budgets} new budgets for user '{user.username}'."
            )
        )
