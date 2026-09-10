# Sprint 11 — Robo-Advisor: Local LLM Layer (Ollama + Qwen3)

**Duration: 2 days.**

## Objective
Turn each `Insight` from Sprint 10 into 2–4 sentences of plain-English coaching using a locally hosted Qwen3:14B model via Ollama. Also builds the LLM-based categorization fallback function that Sprint 13 will wire into Sprint 8's pipeline.

## Preconditions
Sprint 10 complete.

## Firm Decisions
- Model, fixed: `qwen3:14b`. Not user-configurable in v1.
- Ollama endpoint, fixed: `POST {OLLAMA_HOST}/api/chat` with `"stream": false` — never the `/api/generate` endpoint, and never streaming mode (streaming would require the calling view/task to handle partial chunks, which adds complexity with no v1 benefit since advice is short).
- Timeouts, fixed: 60 seconds for `generate_advice`, 30 seconds for `categorize_via_llm` (a much shorter expected response).
- System prompt text is fixed exactly as written below — not templated per user or per rule type in v1.
- Error handling boundary, fixed: `generate_advice` and `categorize_via_llm` **raise** on failure (via `resp.raise_for_status()`) rather than swallowing errors internally — catching and degrading gracefully is the caller's responsibility (Sprint 12's view, Sprint 13's task), not this module's. This keeps the module trivially testable (assert it raises) and keeps failure-handling policy in one place per caller.

## Files
- `advisor/ai.py`
- `advisor/tests/test_ai.py`

## Classes & Functions
`advisor/ai.py`:
```python
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

## Task Breakdown
1. Local dev setup (manual, not code): `ollama serve` in a terminal; `ollama pull qwen3:14b` (confirm the exact tag against `ollama.com/library/qwen3` before pulling — quantization tags can shift)
2. `pip install responses`, confirm it's in `requirements.txt` (already added in Sprint 1's package list)
3. Write `advisor/ai.py` exactly as above
4. Write `advisor/tests/test_ai.py`

## Testing Plan
All tests use `responses.activate` to mock `POST {OLLAMA_HOST}/api/chat` — no test in this suite makes a real network call or requires Ollama running.

`advisor/tests/test_ai.py`:
- `test_generate_advice_calls_ollama_and_saves_message` — mock the endpoint to return `{"message": {"content": "Great job staying under budget..."}}`; call `generate_advice(insight)`; assert an `AdviceMessage` is created with the matching `body` and `model_used == "qwen3:14b"`; inspect the mocked request body and assert it contains a `system` role message and a `user` role message, with `"stream": False`
- `test_build_prompt_includes_all_fields` — call `build_prompt(insight)` directly (no network involved); assert the output string contains the rule key, category name, period dates, and raw_data
- `test_generate_advice_raises_on_http_error` — mock a 500 response; assert calling `generate_advice(insight)` raises `requests.exceptions.HTTPError`, confirming the function does not swallow the error itself
- `test_categorize_via_llm_assigns_matching_category` — mock the response content to exactly match one of the transaction's user's category names; call `categorize_via_llm(transaction)`; assert `transaction.category` is updated and saved
- `test_categorize_via_llm_ignores_unrecognized_answer` — mock the response content to `"UNSURE"`; assert `transaction.category` remains unchanged (`None`)

## Load & Scale
- This module is never called directly from a request-handling view — restated firmly here because it's the layer where that constraint matters most. The only two call sites in the whole project are Sprint 12's advisor-refresh view and Sprint 13's Celery task; both exist specifically so this function's latency (1–30+ seconds depending on hardware) never blocks an HTTP response thread for longer than a user will tolerate without at least a loading indicator (Sprint 12 adds one).
- Hardware sizing, decided as a planning input, not a code change: budget for a host with 12GB+ VRAM if sub-2-second "Refresh insights" responses matter; a CPU-only deployment is functionally correct at this layer but should be planned for 10–30 second response times, not treated as a bug to fix later.

## Definition of Done
- All 5 tests pass with no real Ollama instance running (CI-safe)
- Manual smoke test with Ollama actually running locally: `python manage.py shell` → `from advisor.ai import generate_advice` → call it against a real `Insight` from Sprint 10's smoke test → confirm a real `AdviceMessage` row is created with coherent text
