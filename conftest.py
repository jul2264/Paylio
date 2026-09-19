import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def celery_eager_mode(settings):
    """Ensure celery tasks run eagerly during tests without requiring a real broker."""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True


@pytest.fixture(autouse=True)
def autoclear_cache():
    """Clear cache between test cases to ensure test isolation."""
    cache.clear()
