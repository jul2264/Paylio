from django.core.management.base import BaseCommand
from accounts.models import User
from transactions.models import Category, FinancialAccount


class Command(BaseCommand):
    help = "Seed initial categories and financial account for superuser admin."

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
        for name, kind in categories_data:
            cat, created = Category.objects.get_or_create(
                user=user,
                name=name,
                defaults={"kind": kind},
            )
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

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded: {created_cats} new categories, primary account '{account.name}' (created={acct_created}) for user '{user.username}'."
            )
        )
