from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Category

DEFAULT_CATEGORIES = [
    # Expense categories matching CATEGORY_KEYWORDS
    ("Food & Dining", Category.EXPENSE),
    ("Transport", Category.EXPENSE),
    ("Shopping", Category.EXPENSE),
    ("Subscriptions", Category.EXPENSE),
    ("Utilities", Category.EXPENSE),
    ("Uncategorized", Category.EXPENSE),
    # Income categories
    ("Salary", Category.INCOME),
    ("Freelance", Category.INCOME),
]


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def seed_default_categories(sender, instance, created, **kwargs):
    """Seed 8 default categories for newly registered users."""
    if created:
        for name, kind in DEFAULT_CATEGORIES:
            Category.objects.get_or_create(
                user=instance,
                name=name,
                defaults={"kind": kind},
            )
