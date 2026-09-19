from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom User model for Paylio, unblocking future fields without DB reset."""
    email = models.EmailField(unique=True)
