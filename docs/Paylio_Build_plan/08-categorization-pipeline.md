# Sprint 8 — Expense Categorization Pipeline

**Duration: 3 days.**

## Objective
Automatic category assignment so most transactions never need a manual category pick. Ships as a **3-effective-tier pipeline this sprint** (learned mapping → keyword rules → Uncategorized) — the LLM fallback tier is scaffolded conceptually here but only actually wired to run in Sprint 13, because it depends on Celery infrastructure that doesn't exist until then. This sprint does not guess at that wiring; it leaves an explicit, documented gap that Sprint 13 fills.

## Preconditions
Sprint 7 complete.

## Firm Decisions
- Tier order, fixed: **(1) per-user learned mapping → (2) seeded keyword rules → (3) LLM fallback [wired in Sprint 13] → (4) left as "Uncategorized"**. First match wins; tiers are checked in this exact order, never re-ordered per user or per category.
- The keyword table (`CATEGORY_KEYWORDS`) is fixed to the six seed categories from Sprint 3 — `Food & Dining`, `Transport`, `Shopping`, `Subscriptions`, `Utilities`. (`Salary` has no keyword rule — income categorization is out of scope for the auto-categorizer in v1; income transactions are manually categorized on entry.)
- `normalize_merchant()` strips everything except lowercase letters, digits, and spaces — no fuzzy matching, no Levenshtein distance, no external NLP library. Deliberately simple; if merchant-string noise turns out to defeat this, revisit then.
- A manual correction always writes back into `UserMerchantCategory` via `update_or_create` — Tier 1 is a strict single mapping per `(user, merchant_normalized)`, never a list of past categories to choose from.

## Files
- `transactions/categorization.py`
- `transactions/views.py` (edit: add `transaction_recategorize`; add the `categorize()` call into `transaction_create` from Sprint 7)
- `transactions/urls.py` (edit: add the recategorize route)
- `templates/partials/_transaction_row.html` (edit: add the inline category-correction control)
- `transactions/tests/test_categorization.py`
- `transactions/tests/test_views.py` (edit: add recategorize tests)

## Classes & Functions
`transactions/categorization.py`:
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

    mapping = UserMerchantCategory.objects.filter(
        user=transaction.user, merchant_normalized=normalized
    ).first()
    if mapping:
        transaction.category = mapping.category
        transaction.save(update_fields=["category"])
        return

    for cat_name, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in normalized for kw in keywords):
            category, _ = Category.objects.get_or_create(
                user=transaction.user, name=cat_name, defaults={"kind": Category.EXPENSE}
            )
            transaction.category = category
            transaction.save(update_fields=["category"])
            return

    # Tier 3 (LLM fallback) is wired here in Sprint 13 by replacing this comment
    # with: from advisor.tasks import categorize_with_llm; categorize_with_llm.delay(transaction.id)
    # Until then, an unmatched transaction stays category=None (Uncategorized).


def record_user_correction(transaction, new_category):
    transaction.category = new_category
    transaction.save(update_fields=["category"])
    UserMerchantCategory.objects.update_or_create(
        user=transaction.user,
        merchant_normalized=normalize_merchant(transaction.merchant),
        defaults={"category": new_category},
    )
```

`transactions/views.py` additions:
```python
from django.shortcuts import get_object_or_404
from .categorization import categorize, record_user_correction
from .models import Category

@login_required
def transaction_recategorize(request, pk):
    txn = get_object_or_404(Transaction, pk=pk, user=request.user)
    category = get_object_or_404(Category, pk=request.POST["category"], user=request.user)
    record_user_correction(txn, category)
    return render(request, "partials/_transaction_row.html", {"txn": txn})
```
Edit `transaction_create` (from Sprint 7): immediately after `txn = form.save()`, add:
```python
if txn.category is None:
    categorize(txn)
```

## Task Breakdown
1. Write `transactions/categorization.py` exactly as above
2. Edit `transactions/views.py`: insert the `categorize()` call into `transaction_create`; add `transaction_recategorize`
3. Edit `transactions/urls.py`: add `path("<int:pk>/recategorize/", views.transaction_recategorize, name="recategorize")`
4. Edit `templates/partials/_transaction_row.html`: add an inline `<form hx-post="{% url 'transactions:recategorize' txn.id %}" hx-target="closest tr" hx-swap="outerHTML">` containing a `<select name="category">` of the user's categories, auto-submitting on change (`hx-trigger="change"`)
5. Write `transactions/tests/test_categorization.py`
6. Extend `transactions/tests/test_views.py` with the recategorize tests

## Testing Plan
`transactions/tests/test_categorization.py`:
- `test_normalize_merchant_strips_noise` — `normalize_merchant("SWIGGY* Bangalore #42!")` produces a lowercase, punctuation-free string
- `test_categorize_tier1_learned_mapping_takes_precedence` — create a `UserMerchantCategory` mapping merchant "swiggy hsr" to category `Shopping`; create a transaction with that merchant (which would ALSO match the `Food & Dining` keyword rule); call `categorize()`; assert the category is `Shopping`, proving Tier 1 wins over Tier 2
- `test_categorize_tier2_keyword_match` — transaction merchant `"SWIGGY Koramangala"`, no learned mapping; call `categorize()`; assert category name is `"Food & Dining"`
- `test_categorize_no_match_leaves_uncategorized` — merchant `"XYZ RANDOM 123"`; call `categorize()`; assert `transaction.category is None`
- `test_record_user_correction_updates_transaction_and_learns` — call `record_user_correction(txn, category=Shopping)`; assert `txn.category == Shopping` and a matching `UserMerchantCategory` row exists; call it again for the same merchant with a different category; assert the existing mapping is updated in place (`UserMerchantCategory.objects.count()` unchanged, not incremented)

`transactions/tests/test_views.py` additions:
- `test_recategorize_updates_category_and_learns_mapping` — POST to the recategorize URL, assert the DB reflects both the transaction update and the new mapping
- `test_recategorize_rejects_other_users_transaction` — user B POSTs to recategorize user A's transaction ID, assert 404 (enforced by the `user=request.user` filter in `get_object_or_404`)

## Load & Scale
- Tier 1 lookup (`UserMerchantCategory.objects.filter(...).first()`) hits the implicit index created by `unique_together` — O(1), negligible even run synchronously on every transaction create.
- Tier 2's keyword loop is O(categories × keywords) — fixed at 5 categories / ~20 keywords total; if this grows past a few hundred entries later, revisit as an indexed DB-backed rule table, not needed at this scale.
- Tier 3 is deliberately deferred to an async Celery task (Sprint 13) rather than a synchronous call, specifically so a burst of CSV-imported transactions (Sprint 14) doesn't block the request/import loop on LLM latency — this sprint's design decision only makes sense in light of that constraint, which is why the comment placeholder exists rather than a synchronous stub.

## Definition of Done
- All tests pass, including the existing Sprint 7 suite (unaffected by this sprint's edits)
- In the browser: adding a transaction with merchant text matching a keyword rule auto-assigns the right category with no manual input; manually correcting a category once causes the *next* transaction from that same merchant to auto-categorize correctly without hitting the keyword rules at all
