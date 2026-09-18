from datetime import date
import json
import pytest
import requests
import responses
from django.conf import settings
from accounts.tests.factories import UserFactory
from advisor.ai import build_prompt, categorize_via_llm, generate_advice
from advisor.models import AdviceMessage
from advisor.tests.factories import InsightFactory
from transactions.tests.factories import CategoryFactory, TransactionFactory


@pytest.mark.django_db
@responses.activate
def test_generate_advice_calls_ollama_and_saves_message():
    insight = InsightFactory()
    endpoint = f"{settings.OLLAMA_HOST}/api/chat"
    mock_advice_text = "Great job staying under budget this month. Consider allocating ₹500 to savings."

    responses.add(
        responses.POST,
        endpoint,
        json={"message": {"content": mock_advice_text}},
        status=200,
    )

    msg = generate_advice(insight)

    assert msg.body == mock_advice_text
    assert msg.model_used == "qwen3:14b"
    assert msg.insight == insight
    assert AdviceMessage.objects.filter(insight=insight).count() == 1

    # Verify payload format
    assert len(responses.calls) == 1
    req_body = json.loads(responses.calls[0].request.body)
    assert req_body["model"] == "qwen3:14b"
    assert req_body["stream"] is False
    assert len(req_body["messages"]) == 2
    assert req_body["messages"][0]["role"] == "system"
    assert req_body["messages"][1]["role"] == "user"


@pytest.mark.django_db
def test_build_prompt_includes_all_fields():
    insight = InsightFactory(
        rule_key="budget_overspend",
        period_start=date(2026, 9, 1),
        period_end=date(2026, 9, 30),
        raw_data={"spent": 1200.0, "limit": 1000.0, "pct_over": 20},
    )

    prompt = build_prompt(insight)

    assert "budget_overspend" in prompt
    assert insight.category.name in prompt
    assert "2026-09-01" in prompt
    assert "2026-09-30" in prompt
    assert "1200.0" in prompt
    assert "pct_over" in prompt


@pytest.mark.django_db
@responses.activate
def test_generate_advice_raises_on_http_error():
    insight = InsightFactory()
    endpoint = f"{settings.OLLAMA_HOST}/api/chat"

    responses.add(
        responses.POST,
        endpoint,
        json={"error": "Internal server error"},
        status=500,
    )

    with pytest.raises(requests.exceptions.HTTPError):
        generate_advice(insight)

    assert AdviceMessage.objects.count() == 0


@pytest.mark.django_db
@responses.activate
def test_categorize_via_llm_assigns_matching_category():
    user = UserFactory()
    cat1 = CategoryFactory(user=user, name="Food & Dining")
    CategoryFactory(user=user, name="Transport")
    txn = TransactionFactory(user=user, merchant="Bikanervala", category=None)

    endpoint = f"{settings.OLLAMA_HOST}/api/chat"
    responses.add(
        responses.POST,
        endpoint,
        json={"message": {"content": "Food & Dining"}},
        status=200,
    )

    categorize_via_llm(txn)
    txn.refresh_from_db()

    assert txn.category == cat1


@pytest.mark.django_db
@responses.activate
def test_categorize_via_llm_ignores_unrecognized_answer():
    user = UserFactory()
    CategoryFactory(user=user, name="Food & Dining")
    txn = TransactionFactory(user=user, merchant="XYZ 999", category=None)

    endpoint = f"{settings.OLLAMA_HOST}/api/chat"
    responses.add(
        responses.POST,
        endpoint,
        json={"message": {"content": "UNSURE"}},
        status=200,
    )

    categorize_via_llm(txn)
    txn.refresh_from_db()

    assert txn.category is None
