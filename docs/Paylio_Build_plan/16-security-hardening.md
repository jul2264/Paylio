# Sprint 16 — Security Hardening

**Duration: 2 days.**

## Objective
Build the reusable encrypted-storage mechanism and account-security controls **before** Sprints 14b (Account Aggregator) and 15 (broker integration) ever store a real third-party credential. This sprint is scheduled by file number as Step 16, but must be *executed* immediately after Sprint 13 and before Sprint 14b — see the Sprint 0 overview's numbering note.

## Preconditions
Sprint 1 only (`FIELD_ENCRYPTION_KEY` already exists in `.env`/settings).

## Firm Decisions
- Encryption mechanism: `cryptography`'s `Fernet`, wrapped in a custom Django field (`EncryptedTextField`) — not the `django-cryptography` package's own field class. `cryptography` is installed directly (`pip install cryptography`; it's also a transitive dependency of `django-cryptography` from Sprint 1's package list, but depend on it explicitly rather than implicitly).
- `EncryptedTextField` lives in `integrations/fields.py` — the single shared implementation every app needing encrypted storage imports (Sprint 15's `investments` app included), never duplicated.
- **`BankConsent` is created in this sprint**, not Sprint 14 — it's the natural proving ground for the encrypted field (Sprint 14b then only adds the consent-flow *views* on top of this already-existing model, it does not define new encrypted-storage models of its own).
- Production-only settings (`SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS`) are wrapped in `if not DEBUG:` — forcing HTTPS locally would break `runserver` during development.
- 2FA via `django-otp` (TOTP), enforced with `@otp_required`, applied **only** to the specific views that create or refresh a bank/broker credential (Sprint 14b's consent views, Sprint 15's broker-connect views) — not site-wide. Scoped precisely to where the actual risk is, not blanket-applied.

## Files
- `integrations/fields.py`
- `integrations/models.py`
- `integrations/admin.py`
- `integrations/migrations/0001_initial.py` (generated)
- `config/settings.py` (edit: production security settings, `django_otp` app + middleware)
- `templates/accounts/otp_setup.html`
- `accounts/views.py` (edit: add `otp_setup` view)
- `accounts/urls.py` (edit: add the route)
- `integrations/tests/test_fields.py`

## Classes & Functions
`integrations/fields.py`:
```python
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
```

`integrations/models.py`:
```python
from django.conf import settings
from django.db import models
from .fields import EncryptedTextField

class BankConsent(models.Model):
    PENDING, ACTIVE, REVOKED, EXPIRED = "PENDING", "ACTIVE", "REVOKED", "EXPIRED"
    STATUS_CHOICES = [(PENDING, "Pending"), (ACTIVE, "Active"), (REVOKED, "Revoked"), (EXPIRED, "Expired")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    aa_provider = models.CharField(max_length=30, default="setu")
    consent_handle = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    valid_till = models.DateTimeField(null=True, blank=True)
    encrypted_metadata = EncryptedTextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
```

## Task Breakdown
1. `pip install cryptography django-otp qrcode`, add to `requirements.txt`
2. Write `integrations/fields.py` — `EncryptedTextField` exactly as above
3. Write `integrations/models.py` — `BankConsent` exactly as above (Sprint 14b will add fields here only if a genuine gap appears; expect it not to)
4. `integrations/admin.py` — register `BankConsent`
5. `python manage.py makemigrations integrations && python manage.py migrate`
6. `config/settings.py`:
   ```python
   if not DEBUG:
       SECURE_SSL_REDIRECT = True
       SESSION_COOKIE_SECURE = True
       CSRF_COOKIE_SECURE = True
       SECURE_HSTS_SECONDS = 31536000
   INSTALLED_APPS += ["django_otp", "django_otp.plugins.otp_totp"]
   MIDDLEWARE.insert(MIDDLEWARE.index("django.contrib.auth.middleware.AuthenticationMiddleware") + 1,
                      "django_otp.middleware.OTPMiddleware")
   ```
7. Add `accounts/views.py: otp_setup` — creates a `TOTPDevice` for the user if none exists, renders a QR code (via `qrcode`) of the provisioning URI, and a form to confirm the first generated code before marking the device confirmed
8. `templates/accounts/otp_setup.html` — QR image + confirmation form
9. `accounts/urls.py` — add `path("otp-setup/", views.otp_setup, name="otp_setup")`
10. Write `integrations/tests/test_fields.py`

## Testing Plan
`integrations/tests/test_fields.py`:
- `test_encrypted_field_roundtrip` — create a `BankConsent` with `encrypted_metadata="secret-payload-123"`, save, fetch a **fresh** instance from the DB (`BankConsent.objects.get(pk=...)`, not the in-memory object), assert the fetched value equals the original plaintext
- `test_encrypted_field_stores_ciphertext_not_plaintext` — after saving, query the raw column value directly (`with connection.cursor() as cur: cur.execute("SELECT encrypted_metadata FROM integrations_bankconsent WHERE id=%s", [pk])`), assert the literal string `"secret-payload-123"` does **not** appear in the raw stored value — the test that actually proves encryption is happening, not just that the Python-level round-trip works

## Load & Scale
Not a load/performance sprint — this is a correctness/security sprint. One relevant note for later: Fernet encryption/decryption is fast enough (sub-millisecond) that it's never the bottleneck in any of Sprint 14b/15's sync tasks; no caching or optimization consideration needed here.

## Definition of Done
- Both tests pass, including the raw-SQL ciphertext check
- `/accounts/otp-setup/` renders a real scannable QR code and correctly confirms a code from an authenticator app
- `python manage.py makemigrations --check --dry-run` clean
