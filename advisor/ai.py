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
    from transactions.models import Category

    categories = list(Category.objects.filter(user=transaction.user).values_list("name", flat=True))
    resp = requests.post(
        f"{settings.OLLAMA_HOST}/api/chat",
        json={
            "model": MODEL_NAME,
            "messages": [
                {
                    "role": "system",
                    "content": "Reply with exactly one category name from the list, or UNSURE. No punctuation, no explanation.",
                },
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
