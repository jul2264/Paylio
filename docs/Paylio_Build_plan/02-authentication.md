# Sprint 2 — Authentication & User Accounts

**Duration: 1 day.**

## Objective
Per-user login using Django's built-in auth, with a custom `User` model wired in before any other table exists.

## Preconditions
Sprint 1 complete. This must happen **before the first `migrate`** — `AUTH_USER_MODEL` is baked into every migration with a `ForeignKey(User)`; changing it after tables exist means a full database reset.

## Firm Decisions
- `django.contrib.auth` only — no `django-allauth`, no social login, no email verification flow in v1. Signup is username + password via `UserCreationForm`.
- Custom user model (`accounts.User`, subclassing `AbstractUser`) even though it adds no fields yet — this is the one decision that is materially more expensive to change later than to set up now.
- Session-based auth for the web app (cookies). Token-based auth for mobile arrives in Sprint 19 and does not replace this — they coexist.

## Files
- `accounts/models.py`
- `accounts/urls.py`
- `accounts/views.py`
- `accounts/migrations/0001_initial.py` (generated)
- `templates/accounts/login.html`
- `templates/accounts/signup.html`
- `accounts/tests/factories.py`
- `accounts/tests/test_views.py`
- `config/settings.py` (edit: confirm `AUTH_USER_MODEL`)
- `config/urls.py` (edit: include `accounts.urls`, `dashboard.urls`, `transactions.urls`, `budgets.urls`, `advisor.urls` — the last three are placeholders that 404 until their own sprints land; wiring them now avoids repeated `config/urls.py` edits later)

## Classes & Functions
- `accounts.models.User(AbstractUser)` — no extra fields yet; the class exists so it can gain fields later (currency preference, timezone) without a model-swap migration
- `accounts.views.SignupView(CreateView)` — `model=User`, `form_class=UserCreationForm`, `template_name="accounts/signup.html"`, `success_url=reverse_lazy("login")`

## Task Breakdown
1. Write `accounts/models.py` — `User(AbstractUser): pass`
2. Confirm `AUTH_USER_MODEL = "accounts.User"` is already in `config/settings.py` from Sprint 1
3. Write `accounts/views.py` — `SignupView`
4. Write `accounts/urls.py` — `login/`, `logout/`, `signup/` routes, using `django.contrib.auth.views.LoginView`/`LogoutView` for the first two
5. Write `templates/accounts/login.html` and `signup.html` — plain forms, no styling yet (Sprint 5 supplies the base template and Tailwind classes; these two templates get restyled then, not now)
6. Edit `config/urls.py`: `include("accounts.urls")` at `accounts/`, plus placeholder includes for `dashboard`, `transactions`, `budgets`, `advisor` apps (each app needs an empty `urls.py` with `urlpatterns = []` for now if it doesn't exist yet)
7. `python manage.py makemigrations accounts`
8. `python manage.py migrate` — first migration ever run on this database
9. `python manage.py createsuperuser`
10. Write `accounts/tests/factories.py` — `UserFactory(factory.django.DjangoModelFactory)` using `factory.Faker` for username/email, `set_password("testpass123")` in a `@factory.post_generation` hook
11. Write `accounts/tests/test_views.py` — see Testing Plan

## Testing Plan
`accounts/tests/test_views.py`:
- `test_signup_creates_user` — POST valid username/password/password2 to `signup` URL, assert `User.objects.count() == 1` and response redirects to `login`
- `test_signup_rejects_mismatched_passwords` — POST with `password1 != password2`, assert form re-renders with an error, no user created
- `test_login_success_redirects_to_dashboard` — create a user via `UserFactory`, POST correct credentials to `login`, assert redirect to `LOGIN_REDIRECT_URL`
- `test_login_failure_shows_error` — POST wrong password, assert 200 (re-render) with form error, no session created
- `test_logout_clears_session` — log a client in, POST to `logout`, assert subsequent request to a `@login_required` view redirects to login

## Load & Scale
- `django-axes` is installed now (already in `requirements.txt` from Sprint 1's package list — add it explicitly here: `pip install django-axes`, add to `INSTALLED_APPS` and `AUTHENTICATION_BACKENDS`) with the lockout policy fixed in the Sprint 0 overview (5 failed attempts / 1 hour). This is a security control, not a performance one, but it belongs in this sprint specifically since it wraps the login view being built right here — bolting it on later means re-touching this same code.

## Definition of Done
- All 5 tests in `test_views.py` pass
- `createsuperuser` works and `/admin/` login succeeds
- A brand-new user can sign up, log in, and log out through the actual browser, not just tests
