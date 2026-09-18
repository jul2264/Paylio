from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models


def _fernet():
    return Fernet(settings.FIELD_ENCRYPTION_KEY.encode())


class EncryptedTextField(models.TextField):
    def get_prep_value(self, value):
        if value is None:
            return value
        return _fernet().encrypt(value.encode()).decode()

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return _fernet().decrypt(value.encode()).decode()
