from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Custom User model for Paylio, unblocking future fields without DB reset."""
    pass
