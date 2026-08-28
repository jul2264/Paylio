# Spending Tracker + Robo-Advisor — Full Implementation Guide

A step-by-step build manual: what to build, in what order, with working code for every piece. Each step says **what** it does, **where** it lives in the project, **when** to build it relative to other steps, and **how** to implement it.

**Stack:** Django 5.x · PostgreSQL · Redis · Celery · Django-HTMX · Alpine.js · Tailwind CSS · Chart.js · Ollama running Qwen3:14B · RBI Account Aggregator framework (open banking) · Kite Connect / AA-CAS (demat holdings)

**Assumption carried through:** built for the Indian market (Account Aggregator for banking + investment data, Indian broker APIs for demat holdings). Say so if that's wrong and the relevant steps (14, 15) will change.

## Table of Contents
1. Environment & Project Setup
2. Authentication & User Accounts
3. Core Domain Models
4. Budgets App
5. Frontend Foundation (Tailwind, HTMX, Alpine)
6. Dashboard & Spending Visualization
7. Transaction Management (CRUD + HTMX)
8. Expense Categorization Pipeline
9. Budget Tracking UI
10. Robo-Advisor — Rule Engine
11. Robo-Advisor — Local LLM Layer (Ollama + Qwen3)
12. Advisor Feed UI
13. Background Jobs (Celery)
14. Open Banking Integration
15. Investment / Demat Integration
16. Security Hardening
17. Deployment
18. Live Precious Metal Rates (Gold / Silver / Platinum)
19. Mobile Apps — iOS & Android (React Native)

---

## STEP 1 — Environment & Project Setup

**What:** the project skeleton, dependencies, and configuration everything else builds on.
**When:** first, before any app-specific code.
**Where:** project root.

Prerequisites: Python 3.12+, PostgreSQL 15+, Redis 7+, Node.js (for Tailwind CLI), Ollama installed locally.

```bash
python3 -m venv venv
source venv/bin/activate

pip install django psycopg2-binary python-decouple django-htmx \
            celery redis django-cryptography requests pandas

django-admin startproject config .
python manage.py startapp accounts
python manage.py startapp transactions
python manage.py startapp budgets
python manage.py startapp advisor
python manage.py startapp integrations
python manage.py startapp investments
python manage.py startapp dashboard
```

`.env` (never commit this — add to `.gitignore`):
```
SECRET_KEY=change-me
DEBUG=True
DB_NAME=spendtracker
DB_USER=spendtracker
DB_PASSWORD=change-me
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://localhost:6379/0
OLLAMA_HOST=http://localhost:11434
FIELD_ENCRYPTION_KEY=generate-with-fernet-below
```

Generate the encryption key once (used in Step 16 for token storage):
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

`config/settings.py` — key additions:
```python
from decouple import config as env

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG", default=False, cast=bool)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_htmx",
    "accounts",
    "transactions",
    "budgets",
    "advisor",
    "integrations",
    "investments",
    "dashboard",
]

MIDDLEWARE = [
    # ...defaults...
    "django_htmx.middleware.HtmxMiddleware",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST"),
        "PORT": env("DB_PORT"),
    }
}

AUTH_USER_MODEL = "accounts.User"   # see Step 2 — MUST be set before the first migrate

OLLAMA_HOST = env("OLLAMA_HOST")
FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY")

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"
```

---

## STEP 2 — Authentication & User Accounts

**What:** per-user login, using Django's built-in auth rather than rolling your own.
**When:** immediately after Step 1, **before your first `migrate`**. Django ties `AUTH_USER_MODEL` into every migration that has a `ForeignKey(User)` — changing it after tables exist means resetting your database. Get this right on day one even though the model itself starts nearly empty.
**Where:** `accounts/`.

`accounts/models.py`:
```python
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # Deliberately thin for v1 — a place to add fields (currency preference,
    # timezone, risk tolerance for the advisor) without a painful migration later.
    pass
```

`accounts/urls.py`:
```python
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("signup/", views.SignupView.as_view(), name="signup"),
]
```

`accounts/views.py`:
```python
from django.contrib.auth.forms import UserCreationForm
from django.urls import reverse_lazy
from django.views.generic import CreateView
from .models import User

class SignupView(CreateView):
    model = User
    form_class = UserCreationForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("login")
```

`config/urls.py`:
```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("dashboard.urls")),
    path("transactions/", include("transactions.urls")),
    path("budgets/", include("budgets.urls")),
    path("advisor/", include("advisor.urls")),
]
```

Now run the first migration:
```bash
python manage.py makemigrations accounts
python manage.py migrate
python manage.py createsuperuser
```

Every model from Step 3 onward has `user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)` — reference it via `settings.AUTH_USER_MODEL`, not a direct import of `User`, so app code never cares which user model is active.

---

## STEP 3 — Core Domain Models

**What:** the tables everything else reads and writes — accounts, categories, transactions.
**When:** right after auth; nothing else can be built until these exist.
**Where:** `transactions/models.py`.

```python
from django.conf import settings
from django.db import models


class Category(models.Model):
    INCOME, EXPENSE = "INCOME", "EXPENSE"
    KIND_CHOICES = [(INCOME, "Income"), (EXPENSE, "Expense")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL)
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default=EXPENSE)

    class Meta:
        unique_together = ("user", "name")

    def __str__(self):
        return self.name


class FinancialAccount(models.Model):
    CHECKING, SAVINGS, CREDIT_CARD, CASH = "CHECKING", "SAVINGS", "CREDIT_CARD", "CASH"
    TYPE_CHOICES = [
        (CHECKING, "Checking"), (SAVINGS, "Savings"),
        (CREDIT_CARD, "Credit Card"), (CASH, "Cash"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    account_type = models.CharField(max_length=15, choices=TYPE_CHOICES)
    currency = models.CharField(max_length=3, default="INR")

    def __str__(self):
        return self.name


class Transaction(models.Model):
    MANUAL, BANK_SYNC = "MANUAL", "BANK_SYNC"
    SOURCE_CHOICES = [(MANUAL, "Manual"), (BANK_SYNC, "Bank Sync")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    account = models.ForeignKey(FinancialAccount, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    merchant = models.CharField(max_length=200, blank=True)
    description = models.CharField(max_length=255, blank=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=MANUAL)
    external_id = models.CharField(max_length=200, null=True, blank=True)
    is_recurring = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "date"]),
            models.Index(fields=["user", "category", "date"]),
        ]
        constraints = [
            # dedupe key for bank-sync re-runs — see Step 14
            models.UniqueConstraint(
                fields=["account", "external_id"],
                name="unique_external_txn_per_account",
                condition=models.Q(external_id__isnull=False),
            )
        ]

    def __str__(self):
        return f"{self.merchant} - {self.amount}"


class UserMerchantCategory(models.Model):
    """Tier-1 categorization memory — see Step 8."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    merchant_normalized = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("user", "merchant_normalized")
```

`transactions/admin.py`:
```python
from django.contrib import admin
from .models import Category, FinancialAccount, Transaction, UserMerchantCategory

admin.site.register(Category)
admin.site.register(FinancialAccount)
admin.site.register(Transaction)
admin.site.register(UserMerchantCategory)
```

```bash
python manage.py makemigrations transactions
python manage.py migrate
```

At this point, add a few categories and one account through `/admin/` for your own user — you need seed data before Step 6's dashboard has anything to show.

---

## STEP 4 — Budgets App

**What:** per-category monthly spending limits.
**When:** right after Step 3 — it's a thin model with one dependency (`Category`).
**Where:** `budgets/models.py`.

```python
from django.conf import settings
from django.db import models
from transactions.models import Category


class Budget(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    monthly_limit = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = ("user", "category")

    def __str__(self):
        return f"{self.category} — ₹{self.monthly_limit}/mo"
```

```bash
python manage.py makemigrations budgets
python manage.py migrate
```

---

## STEP 5 — Frontend Foundation

**What:** the base template and asset pipeline every page extends.
**When:** before building any real page (Step 6 onward needs this).
**Where:** `templates/base.html`, `static/`.

Tailwind via CLI (compiled, not the CDN build — the CDN is fine for a quick prototype but ships the whole framework uncompiled to the browser; use the CLI for anything you'll actually run):
```bash
npm install -D tailwindcss
npx tailwindcss init
```

`tailwind.config.js`:
```js
module.exports = {
  content: ["./templates/**/*.html"],
  theme: { extend: {} },
  plugins: [],
};
```

`static/src/input.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

Build/watch during development:
```bash
npx tailwindcss -i ./static/src/input.css -o ./static/css/main.css --watch
```

`templates/base.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{% block title %}Spend Tracker{% endblock %}</title>
    <link rel="stylesheet" href="{% static 'css/main.css' %}">
    <script src="https://unpkg.com/htmx.org@1.9.12"></script>
    <script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    {% load static %}
</head>
<body class="bg-slate-50 text-slate-800 min-h-screen">
    {% include "partials/_nav.html" %}
    <main class="max-w-5xl mx-auto px-4 py-8">
        {% for message in messages %}
            <div class="mb-4 p-3 rounded bg-emerald-50 text-emerald-800">{{ message }}</div>
        {% endfor %}
        {% block content %}{% endblock %}
    </main>
</body>
</html>
```

This one file is why Steps 6–12 don't need to touch frontend tooling again — every later template just extends `base.html` and writes `{% block content %}`.

---

## STEP 6 — Dashboard & Spending Visualization

**What:** the landing page — summary cards, a category breakdown chart, budget bars, advisor feed.
**When:** right after Step 5, using the seed data from Step 3.
**Where:** `dashboard/views.py`.

```python
import json
from datetime import date
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
from transactions.models import Transaction

@login_required
def dashboard(request):
    today = date.today()
    month_txns = Transaction.objects.filter(
        user=request.user, date__year=today.year, date__month=today.month
    )
    total_spent = month_txns.aggregate(total=Sum("amount"))["total"] or 0

    by_category = (
        month_txns.values("category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    chart_labels = [row["category__name"] or "Uncategorized" for row in by_category]
    chart_values = [float(row["total"]) for row in by_category]

    return render(request, "dashboard/dashboard.html", {
        "total_spent": total_spent,
        "chart_labels": json.dumps(chart_labels),
        "chart_values": json.dumps(chart_values),
    })
```

`templates/dashboard/dashboard.html` (relevant excerpt):
```html
{% extends "base.html" %}
{% block content %}
<div class="grid grid-cols-3 gap-4 mb-8">
    <div class="bg-white rounded-xl shadow p-6">
        <p class="text-sm text-slate-500">This month</p>
        <p class="text-2xl font-semibold" id="total-spent">₹{{ total_spent }}</p>
    </div>
</div>

<canvas id="categoryChart" height="100"></canvas>
<script>
    new Chart(document.getElementById('categoryChart'), {
        type: 'doughnut',
        data: {
            labels: {{ chart_labels|safe }},
            datasets: [{ data: {{ chart_values|safe }} }]
        }
    });
</script>

<div hx-get="{% url 'budgets:progress_partial' %}" hx-trigger="load, transactionsChanged from:body"></div>
<div hx-get="{% url 'advisor:feed_partial' %}" hx-trigger="load"></div>
{% endblock %}
```

Note the two `hx-get` divs at the bottom — they're placeholders wired up in Steps 9 and 12. This is the pattern the rest of the app follows: the dashboard shell is built once here, and later steps fill in the partials it already points to.

`dashboard/urls.py`:
```python
from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
]
```

---

## STEP 7 — Transaction Management (CRUD + HTMX)

**What:** manual entry, listing, and filtering — the core loop a user interacts with daily.
**When:** right after the dashboard exists, so you have somewhere to see the effect.
**Where:** `transactions/`.

`transactions/forms.py`:
```python
from django import forms
from .models import Transaction

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ["account", "category", "amount", "date", "merchant", "description"]
```

`transactions/views.py`:
```python
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django_htmx.http import trigger_client_event
from .forms import TransactionForm
from .models import Transaction
from .categorization import categorize

@login_required
def transaction_list(request):
    return render(request, "transactions/list.html", {"form": TransactionForm()})

@login_required
def transaction_table_partial(request):
    qs = Transaction.objects.filter(user=request.user).order_by("-date")
    category = request.GET.get("category")
    if category:
        qs = qs.filter(category_id=category)
    return render(request, "partials/_transaction_table.html", {"transactions": qs[:100]})

@login_required
def transaction_create(request):
    form = TransactionForm(request.POST)
    form.instance.user = request.user
    if form.is_valid():
        txn = form.save()
        if txn.category is None:
            categorize(txn)   # Step 8
        response = render(request, "partials/_transaction_row.html", {"txn": txn})
        return trigger_client_event(response, "transactionsChanged")
    return render(request, "partials/_transaction_form_errors.html", {"form": form})
```

`transactions/urls.py`:
```python
from django.urls import path
from . import views

app_name = "transactions"
urlpatterns = [
    path("", views.transaction_list, name="list"),
    path("table/", views.transaction_table_partial, name="table_partial"),
    path("add/", views.transaction_create, name="create"),
]
```

`templates/transactions/list.html` (key HTMX wiring):
```html
{% extends "base.html" %}
{% block content %}
<form hx-post="{% url 'transactions:create' %}" hx-target="#txn-table-body" hx-swap="afterbegin">
    {{ form.as_p }}
    <button type="submit" class="bg-indigo-600 text-white px-4 py-2 rounded">Add</button>
</form>

<select hx-get="{% url 'transactions:table_partial' %}" hx-target="#txn-table-body" name="category">
    <option value="">All categories</option>
    {% for c in request.user.category_set.all %}<option value="{{ c.id }}">{{ c.name }}</option>{% endfor %}
</select>

<table class="w-full mt-4">
    <tbody id="txn-table-body" hx-get="{% url 'transactions:table_partial' %}" hx-trigger="load">
    </tbody>
</table>
{% endblock %}
```

The `trigger_client_event(response, "transactionsChanged")` call is the piece that makes the dashboard's budget bars and advisor feed (Step 6) refresh themselves the moment a transaction is added — they're independently listening for that event via `hx-trigger="... transactionsChanged from:body"`, with zero coupling to this view.

---

## STEP 8 — Expense Categorization Pipeline

**What:** the 4-tier auto-categorization described in the architecture discussion — implemented for real this time.
**When:** right after transaction entry works, since categorization hooks into transaction creation.
**Where:** `transactions/categorization.py`.

```python
import re
from .models import Category, UserMerchantCategory

def normalize_merchant(raw: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", raw.lower()).strip()

CATEGORY_KEYWORDS = {
    "Food & Dining": ["swiggy", "zomato", "restaurant", "cafe"],
    "Transport":     ["uber", "ola", "rapido", "irctc", "metro"],
    "Shopping":      ["amazon", "flipkart", "myntra"],
    "Subscriptions": ["netflix", "spotify", "prime video", "hotstar"],
    "Utilities":     ["electricity", "broadband", "gas board"],
}

def categorize(transaction):
    normalized = normalize_merchant(transaction.merchant)

    # Tier 1 — learned per-user mapping
    mapping = UserMerchantCategory.objects.filter(
        user=transaction.user, merchant_normalized=normalized
    ).first()
    if mapping:
        transaction.category = mapping.category
        transaction.save(update_fields=["category"])
        return

    # Tier 2 — seeded keyword rules
    for cat_name, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in normalized for kw in keywords):
            category, _ = Category.objects.get_or_create(
                user=transaction.user, name=cat_name, defaults={"kind": Category.EXPENSE}
            )
            transaction.category = category
            transaction.save(update_fields=["category"])
            return

    # Tier 3 — local LLM fallback, queued so the request isn't blocked on it
    from advisor.tasks import categorize_with_llm
    categorize_with_llm.delay(transaction.id)
    # Tier 4 (implicit): if the LLM task also can't decide, it leaves
    # category as None — the UI already treats null category as "Uncategorized".


def record_user_correction(transaction, new_category):
    """Call this from the view that handles a manual category re-assignment
    (an inline HTMX dropdown on the transaction row) — it's what makes Tier 1
    actually learn over time."""
    transaction.category = new_category
    transaction.save(update_fields=["category"])
    UserMerchantCategory.objects.update_or_create(
        user=transaction.user,
        merchant_normalized=normalize_merchant(transaction.merchant),
        defaults={"category": new_category},
    )
```

`advisor/tasks.py` (the Celery task the Tier-3 fallback queues — full Celery setup is Step 13, but the task itself belongs here conceptually):
```python
from celery import shared_task
from .ai import categorize_via_llm

@shared_task
def categorize_with_llm(transaction_id):
    from transactions.models import Transaction
    txn = Transaction.objects.select_related("user").get(id=transaction_id)
    categorize_via_llm(txn)   # implemented in Step 11 alongside the advisor's LLM call
```

**Where the inline "AI-categorized — tap to confirm" UI hooks in:** the transaction row partial (`partials/_transaction_row.html`) reads `txn.category`, and when it was set by the LLM fallback rather than a user, render a small "confirm" affordance next to it that POSTs to a `record_user_correction`-backed view — that confirmation is what feeds the correction back into Tier 1 for next time.

---

## STEP 9 — Budget Tracking UI

**What:** budget-vs-actual progress bars on the dashboard.
**When:** after Step 8, once transactions are reliably categorized (budgets are per-category, so this needs categorization working to be meaningful).
**Where:** `budgets/views.py`.

```python
from datetime import date
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
from .models import Budget
from transactions.models import Transaction

@login_required
def progress_partial(request):
    today = date.today()
    budgets = Budget.objects.filter(user=request.user).select_related("category")
    rows = []
    for b in budgets:
        spent = Transaction.objects.filter(
            user=request.user, category=b.category,
            date__year=today.year, date__month=today.month,
        ).aggregate(total=Sum("amount"))["total"] or 0
        rows.append({
            "budget": b,
            "spent": spent,
            "pct": min(int((spent / b.monthly_limit) * 100), 100) if b.monthly_limit else 0,
            "over": spent > b.monthly_limit,
        })
    return render(request, "partials/_budget_progress.html", {"rows": rows})
```

`templates/partials/_budget_progress.html`:
```html
{% for row in rows %}
<div class="mb-3">
    <div class="flex justify-between text-sm">
        <span>{{ row.budget.category.name }}</span>
        <span class="{% if row.over %}text-red-600{% endif %}">₹{{ row.spent }} / ₹{{ row.budget.monthly_limit }}</span>
    </div>
    <div class="w-full bg-slate-200 rounded-full h-2">
        <div class="h-2 rounded-full transition-all duration-500 {% if row.over %}bg-red-500{% else %}bg-indigo-500{% endif %}"
             style="width: {{ row.pct }}%"></div>
    </div>
</div>
{% endfor %}
```

The `transition-all duration-500` class is the "animation" for this component — a plain CSS transition on the bar's width, no JS animation library needed.

`budgets/urls.py` — this is what the dashboard's `hx-get` from Step 6 already points to:
```python
from django.urls import path
from . import views

app_name = "budgets"
urlpatterns = [
    path("progress/", views.progress_partial, name="progress_partial"),
]
```

---

## STEP 10 — Robo-Advisor: Rule Engine

**What:** deterministic Python rules that detect spending issues and produce `Insight` rows.
**When:** after budgets and categorization both work — the first two rules directly depend on them.
**Where:** `advisor/models.py`, then `advisor/rules.py`.

```python
# advisor/models.py
from django.conf import settings
from django.db import models
from transactions.models import Category

class Insight(models.Model):
    INFO, WARNING, CRITICAL = "INFO", "WARNING", "CRITICAL"
    SEVERITY_CHOICES = [(INFO, "Info"), (WARNING, "Warning"), (CRITICAL, "Critical")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rule_key = models.CharField(max_length=50)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
    period_start = models.DateField()
    period_end = models.DateField()
    summary = models.CharField(max_length=255)
    raw_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class AdviceMessage(models.Model):
    insight = models.ForeignKey(Insight, on_delete=models.CASCADE, related_name="advice")
    body = models.TextField()
    model_used = models.CharField(max_length=50)
    user_feedback = models.CharField(max_length=15, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

```bash
python manage.py makemigrations advisor
python manage.py migrate
```

`advisor/rules.py`:
```python
from datetime import date
from django.db.models import Sum
from budgets.models import Budget
from transactions.models import Transaction
from .models import Insight


class BaseRule:
    key: str
    severity: str

    def evaluate(self, user, period_start, period_end):
        raise NotImplementedError


class BudgetOverspendRule(BaseRule):
    key = "budget_overspend"
    severity = Insight.WARNING

    def evaluate(self, user, period_start, period_end):
        insights = []
        for budget in Budget.objects.filter(user=user).select_related("category"):
            spent = Transaction.objects.filter(
                user=user, category=budget.category, date__range=(period_start, period_end)
            ).aggregate(total=Sum("amount"))["total"] or 0
            if spent > budget.monthly_limit:
                pct_over = round((float(spent) / float(budget.monthly_limit) - 1) * 100)
                insights.append(Insight.objects.create(
                    user=user, rule_key=self.key, severity=self.severity,
                    category=budget.category, period_start=period_start, period_end=period_end,
                    summary=f"{budget.category.name} spending is {pct_over}% over budget",
                    raw_data={"spent": float(spent), "limit": float(budget.monthly_limit), "pct_over": pct_over},
                ))
        return insights


class TrendIncreaseRule(BaseRule):
    key = "trend_increase"
    severity = Insight.INFO
    THRESHOLD_PCT = 30  # flag categories up >30% vs trailing 3-month average

    def evaluate(self, user, period_start, period_end):
        from dateutil.relativedelta import relativedelta
        insights = []
        categories = Transaction.objects.filter(user=user).values_list("category", flat=True).distinct()

        for cat_id in categories:
            if cat_id is None:
                continue
            current = Transaction.objects.filter(
                user=user, category_id=cat_id, date__range=(period_start, period_end)
            ).aggregate(total=Sum("amount"))["total"] or 0

            trailing_totals = []
            for i in range(1, 4):
                m_start = period_start - relativedelta(months=i)
                m_end = m_start.replace(day=28) + relativedelta(day=31)
                total = Transaction.objects.filter(
                    user=user, category_id=cat_id, date__range=(m_start, m_end)
                ).aggregate(total=Sum("amount"))["total"] or 0
                trailing_totals.append(float(total))

            avg = sum(trailing_totals) / len(trailing_totals) if trailing_totals else 0
            if avg > 0 and float(current) > avg * (1 + self.THRESHOLD_PCT / 100):
                pct_increase = round((float(current) / avg - 1) * 100)
                insights.append(Insight.objects.create(
                    user=user, rule_key=self.key, severity=self.severity,
                    category_id=cat_id, period_start=period_start, period_end=period_end,
                    summary=f"Spending up {pct_increase}% vs your 3-month average",
                    raw_data={"current": float(current), "trailing_avg": avg, "pct_increase": pct_increase},
                ))
        return insights


RULES = [BudgetOverspendRule(), TrendIncreaseRule()]


def run_rules_for_user(user, period_start, period_end):
    all_insights = []
    for rule in RULES:
        all_insights.extend(rule.evaluate(user, period_start, period_end))
    return all_insights
```

Note the trailing-average calculation deliberately does the averaging in Python after three simple aggregate queries, rather than one clever ORM window-function query — it's slightly more DB round-trips, but it's code you can read and trust, which matters more than shaving milliseconds for a personal app's data volume.

Add `SavingsRateDropRule`, `RecurringCreepRule`, and `UnusualTransactionRule` the same way once these two are proven — each is a self-contained class, so extending `RULES` is additive and doesn't touch existing rules.

---

## STEP 11 — Robo-Advisor: Local LLM Layer (Ollama + Qwen3)

**What:** turns each `Insight` into 2–4 sentences of plain-English coaching, using a locally hosted model.
**When:** after the rule engine produces real insights — there's nothing to explain until Step 10 works.
**Where:** `advisor/ai.py`.

First, get Ollama running and the model pulled:
```bash
ollama serve            # runs the local API on :11434
ollama pull qwen3:14b   # confirm the exact tag on ollama.com/library/qwen3 at build time
```

Ollama's `/api/chat` endpoint takes a `messages` array (system/user/assistant roles, same shape as most chat APIs) and returns `{"message": {"role": "assistant", "content": "..."}}` when called with `"stream": false`.

```python
# advisor/ai.py
import requests
from django.conf import settings
from .models import AdviceMessage

MODEL_NAME = "qwen3:14b"

SYSTEM_PROMPT = (
    "You are a supportive personal finance coach. Given structured facts about a "
    "user's spending, write 2-4 sentences of specific, encouraging feedback and one "
    "concrete suggested action. Interpret the numbers in plain language rather than "
    "just repeating them."
)

def build_prompt(insight):
    category = insight.category.name if insight.category else "overall spending"
    return (
        f"Rule triggered: {insight.rule_key}\n"
        f"Category: {category}\n"
        f"Period: {insight.period_start} to {insight.period_end}\n"
        f"Facts: {insight.raw_data}\n"
    )

def generate_advice(insight):
    resp = requests.post(
        f"{settings.OLLAMA_HOST}/api/chat",
        json={
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_prompt(insight)},
            ],
            "stream": False,
        },
        timeout=60,
    )
    resp.raise_for_status()
    body = resp.json()["message"]["content"]
    return AdviceMessage.objects.create(insight=insight, body=body, model_used=MODEL_NAME)


def categorize_via_llm(transaction):
    """Tier-3 categorization fallback from Step 8 — same running Ollama instance,
    a much shorter prompt."""
    from transactions.models import Category
    categories = list(Category.objects.filter(user=transaction.user).values_list("name", flat=True))
    resp = requests.post(
        f"{settings.OLLAMA_HOST}/api/chat",
        json={
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": "Reply with exactly one category name from the list, or UNSURE. No punctuation, no explanation."},
                {"role": "user", "content": f"Merchant: {transaction.merchant}\nCategories: {', '.join(categories)}"},
            ],
            "stream": False,
        },
        timeout=30,
    )
    resp.raise_for_status()
    answer = resp.json()["message"]["content"].strip()
    if answer in categories:
        category = Category.objects.get(user=transaction.user, name=answer)
        transaction.category = category
        transaction.save(update_fields=["category"])
```

**Hardware note that affects how you deploy this:** Qwen3:14B at a typical 4-bit quantization needs roughly 9–10GB of RAM/VRAM. On a GPU with 12GB+ VRAM, expect 1–2 second responses; CPU-only, expect tens of seconds — noticeable on an on-demand "refresh insights" button. Decide early whether Ollama runs on the same host as Django (simplest, but competes for resources) or a separate always-on inference box reachable over the network (`OLLAMA_HOST` already makes this a config change, not a code change).

**Failure isolation:** if `requests.post` raises (Ollama down, timeout), catch it in the caller (Step 13's Celery task) and let the `Insight` stand on its own with just its `summary` field — the advice layer is additive, never blocking.

---

## STEP 12 — Advisor Feed UI

**What:** the page/partial where insights + AI advice are actually shown, plus the "refresh" trigger.
**When:** right after Steps 10–11 both work end-to-end.
**Where:** `advisor/views.py`.

```python
from datetime import date
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Insight
from .rules import run_rules_for_user
from .ai import generate_advice

@login_required
def feed_partial(request):
    insights = Insight.objects.filter(user=request.user).prefetch_related("advice").order_by("-created_at")[:10]
    return render(request, "partials/_advisor_feed.html", {"insights": insights})

@login_required
def refresh_insights(request):
    today = date.today()
    period_start = today.replace(day=1)
    new_insights = run_rules_for_user(request.user, period_start, today)
    for insight in new_insights:
        try:
            generate_advice(insight)
        except Exception:
            pass  # insight still stands without AI commentary — see Step 11
    return feed_partial(request)
```

`templates/partials/_advisor_feed.html`:
```html
<div id="advisor-feed">
    <button hx-post="{% url 'advisor:refresh' %}" hx-target="#advisor-feed" hx-swap="outerHTML"
            hx-indicator="#advisor-spinner"
            class="bg-indigo-600 text-white px-4 py-2 rounded mb-4">
        Refresh insights
    </button>
    <span id="advisor-spinner" class="htmx-indicator">Thinking…</span>

    {% for insight in insights %}
    <div class="bg-white rounded-xl shadow p-4 mb-3 transition-opacity duration-300">
        <p class="text-sm text-slate-500">{{ insight.summary }}</p>
        {% for advice in insight.advice.all %}
        <p class="mt-2">{{ advice.body }}</p>
        {% endfor %}
    </div>
    {% endfor %}
</div>
```

`hx-indicator` shows the `#advisor-spinner` element only while the request is in flight — the built-in HTMX pattern for "this might take a few seconds" without writing any JS. This is a synchronous call for v1 (acceptable given Ollama's 1–2s GPU response time); move `refresh_insights` into a Celery task with polling only if you deploy CPU-only and latency becomes genuinely annoying.

`advisor/urls.py` — this is what the dashboard's `hx-get` from Step 6 and the button above both point to:
```python
from django.urls import path
from . import views

app_name = "advisor"
urlpatterns = [
    path("feed/", views.feed_partial, name="feed_partial"),
    path("refresh/", views.refresh_insights, name="refresh"),
]
```

---

## STEP 13 — Background Jobs (Celery)

**What:** async execution for anything slow or external — nightly insight generation, bank sync, broker sync.
**When:** once you have at least one task worth backgrounding (Step 8's LLM categorization fallback already needs this).
**Where:** `config/celery.py`.

```bash
pip install celery redis django-celery-beat
```

`config/celery.py`:
```python
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

`config/__init__.py`:
```python
from .celery import app as celery_app
__all__ = ("celery_app",)
```

`config/settings.py` additions:
```python
CELERY_BROKER_URL = env("REDIS_URL")
CELERY_RESULT_BACKEND = env("REDIS_URL")
CELERY_BEAT_SCHEDULE = {
    "nightly-insights": {
        "task": "advisor.tasks.run_daily_insights",
        "schedule": 60 * 60 * 24,  # every 24h — use crontab() from celery.schedules for a fixed time
    },
}
```

`advisor/tasks.py` (extending the file from Step 8):
```python
from datetime import date
from celery import shared_task
from django.contrib.auth import get_user_model
from .rules import run_rules_for_user
from .ai import generate_advice, categorize_via_llm

@shared_task
def run_daily_insights():
    today = date.today()
    for user in get_user_model().objects.filter(is_active=True):
        for insight in run_rules_for_user(user, today.replace(day=1), today):
            try:
                generate_advice(insight)
            except Exception:
                pass

@shared_task
def categorize_with_llm(transaction_id):
    from transactions.models import Transaction
    txn = Transaction.objects.select_related("user").get(id=transaction_id)
    categorize_via_llm(txn)
```

Run the worker and beat scheduler alongside Django during development:
```bash
celery -A config worker -l info
celery -A config beat -l info
```

---

## STEP 14 — Open Banking Integration

**What:** pulling real bank transactions instead of manual entry.
**When:** deliberately last-but-two — everything above should already work with manual data before you add this. Two sub-paths, build in this order:

### 14a — CSV/statement import (build this first)

**Where:** `transactions/importers.py`. No licensing overhead, gets most of the user value immediately.

```python
import pandas as pd
from .models import Transaction, FinancialAccount
from .categorization import categorize

def import_csv(user, account: FinancialAccount, file):
    df = pd.read_csv(file)
    # Adjust column names to match your bank's actual export format
    for _, row in df.iterrows():
        txn, created = Transaction.objects.get_or_create(
            account=account,
            external_id=str(row.get("Reference No", row.name)),  # dedupe key
            defaults={
                "user": user,
                "amount": abs(row["Amount"]),
                "date": pd.to_datetime(row["Date"]).date(),
                "merchant": str(row.get("Narration", ""))[:200],
                "source": Transaction.BANK_SYNC,
            },
        )
        if created and txn.category is None:
            categorize(txn)
```

`external_id` reuses the same unique constraint from Step 3 — re-uploading the same statement is safe and won't duplicate rows.

### 14b — Account Aggregator integration (build this once 14a is proven)

India's open banking runs through RBI's **Account Aggregator (AA)** framework rather than a Plaid-style model: a licensed NBFC-AA brokers consent between the bank (FIP) and your app (FIU) — you never see the user's net-banking credentials.

Steps:
1. Register a developer/sandbox account with an AA technical provider — **Setu**'s Account Aggregator product is the most commonly used starting point; Finvu and Anumati are alternatives. Sandbox access doesn't require full production FIU licensing.
2. `integrations/models.py` — `BankConsent(user FK, aa_provider, consent_handle, status, valid_till, encrypted_metadata)` (see Step 16 for the encrypted field).
3. Build the consent-request call: your backend calls the AA's consent-request endpoint specifying FI types (`DEPOSIT`, and — per the AA framework's 2026 expansion — potentially `MUTUAL_FUND`/`EQUITIES` too, relevant for Step 15), purpose, and duration.
4. Redirect the user into the AA's hosted consent journey (a webview/redirect flow, not unlike an OAuth consent screen) where they pick their bank and approve.
5. Handle the AA's callback/webhook at `integrations/views.py: consent_webhook` — update `BankConsent.status`.
6. Once approved, call the FI-data-fetch endpoint; the payload arrives encrypted per the AA spec — decrypt with your registered keypair, then map each entry into `Transaction` using the AA's transaction reference as `external_id`.
7. **Exact endpoint paths and payload schemas are provider-specific and do change** — treat this section as the architecture (where each piece lives, how consent and dedupe work) and pull current endpoint details from your chosen AA's live developer docs when you implement it, rather than hardcoding from a guide that may be stale by the time you build it.
8. Production FIU status generally requires RBI recognition — a real step for a commercial launch, likely unnecessary while you're building/testing in sandbox.

---

## STEP 15 — Investment / Demat Integration

**What:** read-only portfolio holdings (equities, mutual funds, bonds).
**When:** last — it's the most operationally complex piece (daily token expiry) and isn't a dependency for anything else.
**Where:** `investments/`, `integrations/brokers/kite.py`.

```python
# investments/models.py
from django.conf import settings
from django.db import models

class BrokerConnection(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    broker = models.CharField(max_length=30)               # "zerodha", "upstox", ...
    encrypted_access_token = models.TextField()             # see Step 16
    token_expires_at = models.DateTimeField()

class Holding(models.Model):
    EQUITY, MUTUAL_FUND, BOND = "EQUITY", "MUTUAL_FUND", "BOND"
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    broker_connection = models.ForeignKey(BrokerConnection, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=50)
    asset_type = models.CharField(max_length=15)
    quantity = models.DecimalField(max_digits=12, decimal_places=4)
    avg_price = models.DecimalField(max_digits=12, decimal_places=2)
    last_synced_price = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    last_synced_at = models.DateTimeField(null=True)

class PortfolioSnapshot(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField()
    total_value = models.DecimalField(max_digits=14, decimal_places=2)
```

Kite Connect integration (`pip install kiteconnect`) — confirmed against the official SDK:

```python
# integrations/brokers/kite.py
from kiteconnect import KiteConnect
from django.conf import settings

def get_login_url():
    kite = KiteConnect(api_key=settings.KITE_API_KEY)
    return kite.login_url()

def exchange_request_token(request_token):
    kite = KiteConnect(api_key=settings.KITE_API_KEY)
    data = kite.generate_session(request_token, api_secret=settings.KITE_API_SECRET)
    return data["access_token"]   # store this encrypted — Step 16

def fetch_holdings(access_token):
    kite = KiteConnect(api_key=settings.KITE_API_KEY)
    kite.set_access_token(access_token)
    return kite.holdings()
```

Django view side (the OAuth-like redirect/callback pair):
```python
# investments/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils import timezone
from datetime import timedelta
from integrations.brokers.kite import get_login_url, exchange_request_token
from .models import BrokerConnection

@login_required
def connect_broker(request):
    return redirect(get_login_url())

@login_required
def broker_callback(request):
    request_token = request.GET["request_token"]
    access_token = exchange_request_token(request_token)
    BrokerConnection.objects.update_or_create(
        user=request.user, broker="zerodha",
        defaults={
            "encrypted_access_token": access_token,  # encrypt before saving — Step 16
            "token_expires_at": timezone.now() + timedelta(hours=20),
        },
    )
    return redirect("dashboard")
```

**The constraint that shapes the whole UX here:** Zerodha (and most Indian brokers) expire access tokens **daily**, with no silent refresh — a manual login (often including TOTP) is required each day by design/regulation. Build the sync as a daily Celery Beat task (`investments/tasks.py: sync_holdings`) that runs `fetch_holdings()` for every non-expired `BrokerConnection`, and surface a clear "reconnect your broker" prompt in the UI once a token has expired — don't design around the assumption that this can ever be fully silent.

For mutual funds/bonds specifically, the more scalable path is extending the Step 14b AA consent flow to cover investment FI types (CAS data from CDSL/NSDL via SEBI-regulated FIPs in the AA network) rather than integrating each broker/RTA separately — worth doing once 14b already exists.

Scope this module as **read-only** (holdings + valuation trend via `PortfolioSnapshot`) — order placement carries materially more regulatory and liability weight than this app's use case needs.

---

## STEP 16 — Security Hardening

**What:** the settings and patterns that matter once real bank/broker tokens are in your database.
**When:** before Step 14b/15 go anywhere near real accounts — not a final "polish" step.
**Where:** `config/settings.py`, `integrations/fields.py`.

```python
# config/settings.py — production-facing settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
```

Encrypted token field using `cryptography`'s Fernet (matches the `FIELD_ENCRYPTION_KEY` generated in Step 1):
```python
# integrations/fields.py
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

Swap `models.TextField()` for `EncryptedTextField()` on `BankConsent.encrypted_metadata` and `BrokerConnection.encrypted_access_token` from Steps 14–15.

Once 14b/15 are live, add `django-otp` for 2FA on login — the blast radius of an account takeover is meaningfully higher once real financial-account tokens sit behind that login.

---

## STEP 17 — Deployment

**What:** running the whole stack (Django, Postgres, Redis, Celery worker + beat, Ollama) together.
**When:** last, once Steps 1–13 work locally.
**Where:** `docker-compose.yml` at project root.

```yaml
version: "3.9"
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: spendtracker
      POSTGRES_USER: spendtracker
      POSTGRES_PASSWORD: change-me
    volumes: ["pgdata:/var/lib/postgresql/data"]

  redis:
    image: redis:7

  ollama:
    image: ollama/ollama
    volumes: ["ollama_models:/root/.ollama"]
    ports: ["11434:11434"]

  web:
    build: .
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000
    depends_on: [db, redis, ollama]
    env_file: .env
    ports: ["8000:8000"]

  celery_worker:
    build: .
    command: celery -A config worker -l info
    depends_on: [db, redis, ollama]
    env_file: .env

  celery_beat:
    build: .
    command: celery -A config beat -l info
    depends_on: [db, redis]
    env_file: .env

volumes:
  pgdata:
  ollama_models:
```

Note `ollama` as its own service with a persistent volume for the model weights (so `ollama pull qwen3:14b` doesn't re-download on every container restart) — and that it competes for the same host's CPU/GPU as everything else, which is the practical version of the hardware note from Step 11. If the host running this doesn't have a GPU, consider pointing `OLLAMA_HOST` at a separate GPU-equipped machine instead of running the `ollama` service locally — it's a one-line env change, not a code change, because Step 11's client only ever talks to `settings.OLLAMA_HOST`.

---

## STEP 18 — Live Precious Metal Rates (Gold / Silver / Platinum)

**What:** gold (24K, 22K, 18K), silver (999 Fine, 958 Britannia, 925 Sterling, 900 Coin, 800 Continental), and platinum (999, 950, 900, 850) rates, refreshed periodically and shown in the app.
**When:** independent of the rest of the domain — build it any time after Step 5 (frontend foundation). It doesn't touch transactions, budgets, or the advisor, so there's no reason to sequence it late; it's placed here in the guide because it's a self-contained addition, not because it depends on Steps 6–17.
**Where:** a new `rates` app.

**Data source:** a third-party spot-price API — GoldAPI.io and metals-api.com both return live XAU (gold) / XAG (silver) / XPT (platinum) spot prices; GoldAPI.io's request shape is `GET https://www.goldapi.io/api/{symbol}/{currency}` with an `x-access-token` header, and it accepts `INR` directly as the currency segment, so it hands back an India-priced spot rate with no separate forex step. Free tiers on these services are rate-limited (check current limits when you sign up) but comfortably enough for periodic polling — see the "on live" note below for why that's fine here.

Only store the **pure** per-gram rate (999 fineness / 24K) per metal per snapshot. Every purity you listed is a fixed multiplier off that one number — storing 12 rows per fetch would just be redundant copies of the same 3 numbers.

`rates/models.py`:
```python
from django.db import models

class MetalRateSnapshot(models.Model):
    GOLD, SILVER, PLATINUM = "GOLD", "SILVER", "PLATINUM"
    METAL_CHOICES = [(GOLD, "Gold"), (SILVER, "Silver"), (PLATINUM, "Platinum")]

    metal = models.CharField(max_length=10, choices=METAL_CHOICES)
    price_per_gram_999 = models.DecimalField(max_digits=10, decimal_places=2)  # INR, pure/finest rate
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["metal", "-fetched_at"])]
```

`rates/purity.py` — the multiplier tables, one place all your requested purities live:
```python
GOLD_PURITIES = {"24K": 1.0, "22K": 22/24, "18K": 18/24}
SILVER_PURITIES = {
    "999 Fine": 0.999, "958 Britannia": 0.958, "925 Sterling": 0.925,
    "900 Coin": 0.900, "800 Continental": 0.800,
}
PLATINUM_PURITIES = {"999": 0.999, "950": 0.950, "900": 0.900, "850": 0.850}

def compute_purity_rates(base_price_per_gram, purity_table):
    return {label: round(base_price_per_gram * factor, 2) for label, factor in purity_table.items()}
```

`rates/fetcher.py`:
```python
import requests
from django.conf import settings

TROY_OUNCE_TO_GRAM = 31.1034768
SYMBOLS = {"GOLD": "XAU", "SILVER": "XAG", "PLATINUM": "XPT"}

def fetch_price_per_gram_inr(metal: str) -> float:
    symbol = SYMBOLS[metal]
    resp = requests.get(
        f"https://www.goldapi.io/api/{symbol}/INR",
        headers={"x-access-token": settings.METALS_API_KEY},
        timeout=15,
    )
    resp.raise_for_status()
    price_per_oz_inr = resp.json()["price"]   # confirm this field name against your provider's current docs before relying on it
    return price_per_oz_inr / TROY_OUNCE_TO_GRAM
```

If you pick a provider that only returns USD, add one forex conversion call before the troy-ounce-to-gram division — GoldAPI.io's INR-in-the-URL support means you likely won't need to.

`rates/tasks.py`, and its `CELERY_BEAT_SCHEDULE` entry alongside the one from Step 13:
```python
from celery import shared_task
from .fetcher import fetch_price_per_gram_inr
from .models import MetalRateSnapshot

@shared_task
def refresh_metal_rates():
    for metal in ["GOLD", "SILVER", "PLATINUM"]:
        MetalRateSnapshot.objects.create(
            metal=metal, price_per_gram_999=fetch_price_per_gram_inr(metal)
        )
```
```python
# config/settings.py — CELERY_BEAT_SCHEDULE
"refresh-metal-rates": {"task": "rates.tasks.refresh_metal_rates", "schedule": 60 * 30},
```

**On "live":** Indian retail bullion rates (what jewelers actually quote) typically update once or twice a day even on jeweler websites, tracking the international spot market with a lag — polling every 15–30 minutes is genuinely "live" for this use case, comfortably within any free-tier rate limit, and matches the cadence users actually expect. True tick-by-tick streaming is what a trading platform needs, not a personal finance app's metal-rate display.

`rates/views.py` and the widget template:
```python
from django.views.decorators.http import require_GET
from django.shortcuts import render
from .models import MetalRateSnapshot
from .purity import GOLD_PURITIES, SILVER_PURITIES, PLATINUM_PURITIES, compute_purity_rates

@require_GET
def rates_widget(request):
    context = {}
    for metal, purity_table, key in [
        ("GOLD", GOLD_PURITIES, "gold"),
        ("SILVER", SILVER_PURITIES, "silver"),
        ("PLATINUM", PLATINUM_PURITIES, "platinum"),
    ]:
        latest = MetalRateSnapshot.objects.filter(metal=metal).order_by("-fetched_at").first()
        context[key] = compute_purity_rates(float(latest.price_per_gram_999), purity_table) if latest else {}
    return render(request, "partials/_metal_rates.html", context)
```

`rates/urls.py`:
```python
from django.urls import path
from . import views

app_name = "rates"
urlpatterns = [path("widget/", views.rates_widget, name="widget")]
```

`templates/partials/_metal_rates.html`, using HTMX's `every Ns` trigger for client-side polling — matched to the 30-minute server-side refresh cadence, not tighter:
```html
<div hx-get="{% url 'rates:widget' %}" hx-trigger="load, every 300s" class="grid grid-cols-3 gap-4">
    <div class="bg-white rounded-xl shadow p-4">
        <p class="font-semibold mb-2">Gold <span class="text-xs text-slate-400">/ gram</span></p>
        {% for karat, price in gold.items %}
        <div class="flex justify-between text-sm"><span>{{ karat }}</span><span>₹{{ price }}</span></div>
        {% endfor %}
    </div>
    <div class="bg-white rounded-xl shadow p-4">
        <p class="font-semibold mb-2">Silver <span class="text-xs text-slate-400">/ gram</span></p>
        {% for purity, price in silver.items %}
        <div class="flex justify-between text-sm"><span>{{ purity }}</span><span>₹{{ price }}</span></div>
        {% endfor %}
    </div>
    <div class="bg-white rounded-xl shadow p-4">
        <p class="font-semibold mb-2">Platinum <span class="text-xs text-slate-400">/ gram</span></p>
        {% for purity, price in platinum.items %}
        <div class="flex justify-between text-sm"><span>{{ purity }}</span><span>₹{{ price }}</span></div>
        {% endfor %}
    </div>
</div>
```

Drop `{% include "partials/_metal_rates.html" %}` (or an equivalent `hx-get` div) into the Step 6 dashboard template — it's a third independent widget alongside the budget-progress and advisor-feed ones, following the exact same pattern.

Wire-up: add `"rates"` to `INSTALLED_APPS`, `path("rates/", include("rates.urls"))` to `config/urls.py`, and `METALS_API_KEY` to `.env`/settings alongside the keys from Step 1.

---

## STEP 19 — Mobile Apps: iOS & Android (React Native)

**What:** native iOS and Android apps, backed by a JSON API on top of the same Django backend.
**When:** after Steps 1–13 have a working backend (and ideally 18, so the rates widget has something to consume) — build the API layer first, then the app. Don't start the React Native app against endpoints that don't exist yet.
**Where:** a new `api` Django app, plus a separate `mobile/` React Native (Expo) project — separate build pipelines, no shared tooling, but both talk to the one Django backend.

**The governing principle for this whole step:** one backend, two presentation layers, shared business logic. The DRF views below must not reimplement categorization, rule evaluation, or purity computation — they call the exact same functions the HTMX views already call (`categorize()` from Step 8, `run_rules_for_user()`/`generate_advice()` from Steps 10–11, `compute_purity_rates()` from Step 18). If any of those steps ended up with the logic written inline inside the view function rather than factored out, the prerequisite here is a small refactor: pull the query/computation into a plain function, have both the HTML view and the new DRF view call it. Skipping this and writing the mobile API's logic separately is how the two frontends quietly drift out of sync over time.

### 19a — Django REST Framework API layer

```bash
pip install djangorestframework djangorestframework-simplejwt
python manage.py startapp api
```

`config/settings.py` additions:
```python
INSTALLED_APPS += ["rest_framework", "api"]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
}

from datetime import timedelta
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
}
```

Session-cookie auth (used by the HTMX web app) and JWT auth (used by the mobile app) coexist fine — they're just two different `DEFAULT_AUTHENTICATION_CLASSES` entries, and Django's ordinary `@login_required` views are untouched by adding DRF's JWT authentication for the `/api/` routes.

`api/serializers.py`:
```python
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from transactions.models import Transaction, Category
from budgets.models import Budget
from advisor.models import Insight, AdviceMessage

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "kind", "parent"]

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ["id", "account", "category", "amount", "date", "merchant", "description", "source", "is_recurring"]
        read_only_fields = ["source"]

class BudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = ["id", "category", "monthly_limit"]

class AdviceMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdviceMessage
        fields = ["id", "body", "created_at"]

class InsightSerializer(serializers.ModelSerializer):
    advice = AdviceMessageSerializer(many=True, read_only=True)
    class Meta:
        model = Insight
        fields = ["id", "rule_key", "severity", "category", "summary", "raw_data", "created_at", "advice"]

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    class Meta:
        model = get_user_model()
        fields = ["username", "email", "password"]

    def create(self, validated_data):
        return get_user_model().objects.create_user(**validated_data)
```

`api/views.py`:
```python
from datetime import date
from django.db.models import Sum
from rest_framework import viewsets, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from transactions.models import Transaction, Category
from transactions.categorization import categorize
from budgets.models import Budget
from advisor.models import Insight
from advisor.rules import run_rules_for_user
from advisor.ai import generate_advice
from .serializers import (
    TransactionSerializer, CategorySerializer, BudgetSerializer,
    InsightSerializer, UserRegistrationSerializer,
)


class RegisterView(generics.CreateAPIView):
    queryset = None
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        from django.contrib.auth import get_user_model
        return get_user_model().objects.all()


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user).order_by("-date")

    def perform_create(self, serializer):
        txn = serializer.save(user=self.request.user)
        if txn.category is None:
            categorize(txn)   # same Step 8 function the HTMX view calls — not reimplemented here


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)


class BudgetViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)


@api_view(["GET"])
def dashboard_summary(request):
    today = date.today()
    qs = Transaction.objects.filter(user=request.user, date__year=today.year, date__month=today.month)
    total = qs.aggregate(total=Sum("amount"))["total"] or 0
    by_category = list(qs.values("category__name").annotate(total=Sum("amount")).order_by("-total"))
    return Response({"total_spent": total, "by_category": by_category})


@api_view(["GET"])
def advisor_feed(request):
    insights = Insight.objects.filter(user=request.user).prefetch_related("advice").order_by("-created_at")[:10]
    return Response(InsightSerializer(insights, many=True).data)


@api_view(["POST"])
def advisor_refresh(request):
    today = date.today()
    for insight in run_rules_for_user(request.user, today.replace(day=1), today):
        try:
            generate_advice(insight)
        except Exception:
            pass
    return advisor_feed(request)


@api_view(["GET"])
@permission_classes([AllowAny])
def metal_rates(request):
    from rates.models import MetalRateSnapshot
    from rates.purity import GOLD_PURITIES, SILVER_PURITIES, PLATINUM_PURITIES, compute_purity_rates
    data = {}
    for metal, table, key in [
        ("GOLD", GOLD_PURITIES, "gold"), ("SILVER", SILVER_PURITIES, "silver"), ("PLATINUM", PLATINUM_PURITIES, "platinum"),
    ]:
        latest = MetalRateSnapshot.objects.filter(metal=metal).order_by("-fetched_at").first()
        data[key] = compute_purity_rates(float(latest.price_per_gram_999), table) if latest else {}
    return Response(data)
```

`dashboard_summary`, `advisor_feed`/`advisor_refresh`, and `metal_rates` are the JSON twins of the exact HTML-returning views from Steps 6, 12, and 18 — same queries, same underlying functions, different final call (`Response()` instead of `render()`).

`api/urls.py`:
```python
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

router = DefaultRouter()
router.register("transactions", views.TransactionViewSet, basename="transaction")
router.register("categories", views.CategoryViewSet, basename="category")
router.register("budgets", views.BudgetViewSet, basename="budget")

urlpatterns = [
    path("register/", views.RegisterView.as_view()),
    path("token/", TokenObtainPairView.as_view()),
    path("token/refresh/", TokenRefreshView.as_view()),
    path("dashboard/summary/", views.dashboard_summary),
    path("advisor/feed/", views.advisor_feed),
    path("advisor/refresh/", views.advisor_refresh),
    path("rates/", views.metal_rates),
    path("", include(router.urls)),
]
```

Add `path("api/v1/", include("api.urls"))` to `config/urls.py` — versioned from day one, so a breaking mobile-API change later is `/api/v2/`, not a break for whatever version of the app is already installed on someone's phone.

**On CORS:** `django-cors-headers` is a browser same-origin mechanism — a compiled native iOS/Android app's networking layer isn't a browser and isn't subject to it, so you don't need it for the app itself. Only add it if you use Expo's web preview (`expo start --web`) during development or ever add a browser-based client hitting this API.

### 19b — React Native (Expo) app

```bash
npx create-expo-app mobile
cd mobile
npx expo install expo-secure-store @react-navigation/native @react-navigation/bottom-tabs react-native-chart-kit
npm install @tanstack/react-query
```

```
mobile/
├── App.tsx
├── app.config.js            # EXPO_PUBLIC_API_BASE_URL per environment
└── src/
    ├── api/
    │   ├── client.ts         # fetch wrapper, attaches JWT
    │   └── hooks.ts          # React Query hooks, one per resource
    ├── auth/
    │   └── AuthContext.tsx   # tokens, login/logout, gates navigation
    ├── navigation/
    │   └── TabNavigator.tsx  # mirrors the web app's five sections
    └── screens/
        ├── LoginScreen.tsx
        ├── DashboardScreen.tsx
        ├── TransactionsScreen.tsx
        ├── BudgetsScreen.tsx
        ├── AdvisorScreen.tsx
        └── RatesScreen.tsx
```

`src/api/client.ts`:
```typescript
import * as SecureStore from "expo-secure-store";

const API_BASE = process.env.EXPO_PUBLIC_API_BASE_URL;

async function request(path: string, options: RequestInit = {}) {
  const token = await SecureStore.getItemAsync("access_token");
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (res.status === 401) {
    // attempt POST /token/refresh/ with the stored refresh token, retry once;
    // on second failure, clear SecureStore and route to LoginScreen
  }
  return res.json();
}

export const api = {
  get: (path: string) => request(path),
  post: (path: string, body: unknown) => request(path, { method: "POST", body: JSON.stringify(body) }),
};
```

Never use plain `AsyncStorage` for the tokens — it's unencrypted on-disk storage. `expo-secure-store` backs onto the platform Keychain (iOS) / Keystore (Android), which is the appropriate place for auth tokens given this app also handles financial account tokens elsewhere (Step 16's encryption concern applies to how the client stores its own credentials too, not just what the server stores).

`src/api/hooks.ts`:
```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";

export function useTransactions() {
  return useQuery({ queryKey: ["transactions"], queryFn: () => api.get("/transactions/") });
}

export function useAddTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (txn: object) => api.post("/transactions/", txn),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["dashboard-summary"] });
      qc.invalidateQueries({ queryKey: ["budget-progress"] });
    },
  });
}

export function useDashboardSummary() {
  return useQuery({ queryKey: ["dashboard-summary"], queryFn: () => api.get("/dashboard/summary/") });
}

export function useMetalRates() {
  return useQuery({
    queryKey: ["metal-rates"],
    queryFn: () => api.get("/rates/"),
    refetchInterval: 5 * 60 * 1000,   // mirrors the HTMX "every 300s" poll from Step 18
  });
}

export function useAdvisorFeed() {
  return useQuery({ queryKey: ["advisor-feed"], queryFn: () => api.get("/advisor/feed/") });
}

export function useRefreshAdvisor() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post("/advisor/refresh/", {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["advisor-feed"] }),
  });
}
```

The design parallel worth noticing: `onSuccess: qc.invalidateQueries(...)` here is doing exactly what `HX-Trigger: transactionsChanged` does on the web side (Step 7) — "something changed, dependent views should refetch." Same idea, platform-appropriate mechanism; this is *why* Steps 6–12/18 were built around discrete, independently-refreshable widgets in the first place — that shape ports directly to React Query's cache-invalidation model instead of needing to be redesigned for mobile.

`src/navigation/TabNavigator.tsx`:
```tsx
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import DashboardScreen from "../screens/DashboardScreen";
import TransactionsScreen from "../screens/TransactionsScreen";
import BudgetsScreen from "../screens/BudgetsScreen";
import AdvisorScreen from "../screens/AdvisorScreen";
import RatesScreen from "../screens/RatesScreen";

const Tab = createBottomTabNavigator();

export default function TabNavigator() {
  return (
    <Tab.Navigator>
      <Tab.Screen name="Dashboard" component={DashboardScreen} />
      <Tab.Screen name="Transactions" component={TransactionsScreen} />
      <Tab.Screen name="Budgets" component={BudgetsScreen} />
      <Tab.Screen name="Advisor" component={AdvisorScreen} />
      <Tab.Screen name="Rates" component={RatesScreen} />
    </Tab.Navigator>
  );
}
```
Five tabs mapping almost 1:1 onto the web app's five URL sections (`/`, `/transactions/`, `/budgets/`, `/advisor/`, `/rates/widget/`) — same information architecture, native presentation.

`src/screens/DashboardScreen.tsx` (the React Query + chart pattern every other screen follows):
```tsx
import { View, Text } from "react-native";
import { PieChart } from "react-native-chart-kit";
import { useDashboardSummary } from "../api/hooks";

export default function DashboardScreen() {
  const { data, isLoading } = useDashboardSummary();
  if (isLoading || !data) return <Text>Loading…</Text>;

  return (
    <View style={{ padding: 16 }}>
      <Text style={{ fontSize: 24, fontWeight: "600" }}>₹{data.total_spent}</Text>
      <PieChart
        data={data.by_category.map((c: any) => ({
          name: c.category__name ?? "Uncategorized",
          population: c.total,
          color: "#6366f1",
          legendFontColor: "#334155",
        }))}
        width={320} height={200} accessor="population"
        backgroundColor="transparent" paddingLeft="0"
        chartConfig={{ color: () => "#6366f1" }}
      />
    </View>
  );
}
```

### 19c — Push notifications (a natural extension, not a new system)

The Celery-driven rule engine (Steps 10, 13) already generates `Insight` rows server-side — wiring push notifications is small incremental work on top of that, not a new system to design. Add a `DeviceToken(user, expo_push_token)` model, register the token from the RN app via `expo-notifications` right after login, and call Expo's push API from `advisor/tasks.py` whenever a `CRITICAL`-severity `Insight` is created — reusing the exact trigger point that already exists rather than building a second notification pipeline.

### 19d — Building and shipping

```bash
npm install -g eas-cli
eas build --platform ios
eas build --platform android
```

EAS Build compiles both the iOS `.ipa` and Android `.aab`/`.apk` in the cloud — notably, this means you can produce an iOS build without owning a Mac, which is otherwise a hard requirement for iOS development. You'll still need an active Apple Developer account (paid, annual) to submit to the App Store, and a one-time Google Play Developer registration fee for the Play Store. Budget real calendar time for both stores' review processes — Apple's especially can take several days and occasionally comes back with requested changes — this is a fundamentally different release cadence than "push to the Django server" from Step 17, worth planning for as its own timeline, not an afterthought at the end of a sprint.

Point `EXPO_PUBLIC_API_BASE_URL` at your deployed Django host (Step 17) for these builds, not `localhost` — `localhost` only resolves correctly for Expo Go's dev client running on the same network as your development machine.