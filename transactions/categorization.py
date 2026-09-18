import re
from .models import Category, UserMerchantCategory


def normalize_merchant(raw: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", raw.lower()).strip()


CATEGORY_KEYWORDS = {
    "Food & Dining": ["swiggy", "zomato", "restaurant", "cafe"],
    "Transport": ["uber", "ola", "rapido", "irctc", "metro"],
    "Shopping": ["amazon", "flipkart", "myntra"],
    "Subscriptions": ["netflix", "spotify", "prime video", "hotstar"],
    "Utilities": ["electricity", "broadband", "gas board"],
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
