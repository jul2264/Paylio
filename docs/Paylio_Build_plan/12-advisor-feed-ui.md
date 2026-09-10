# Sprint 12 — Advisor Feed UI

**Duration: 2 days.**

## Objective
The page/partial where insights and AI advice are actually shown, plus the on-demand "Refresh insights" trigger — the user-facing surface for Sprints 10–11's work.

## Preconditions
Sprints 10 and 11 complete.

## Firm Decisions
- `refresh_insights` is a **synchronous** view call in v1 (runs the rule engine + LLM calls in-request, not via Celery) — acceptable given Sprint 11's GPU-hardware target of 1–2 second Ollama responses; an `hx-indicator` spinner covers the wait. Moving this to async+polling is deferred until a CPU-only deployment makes the synchronous wait genuinely unacceptable — not built preemptively.
- Each insight's `generate_advice` call is wrapped in its own `try/except` inside the loop — one failed AI call must never prevent the other insights on the same refresh from getting their advice or from being displayed.
- Feed shows the **10 most recent** insights, no further pagination in v1.

## Files
- `advisor/views.py`
- `advisor/urls.py`
- `templates/partials/_advisor_feed.html`
- `templates/dashboard/dashboard.html` (edit: add the advisor-feed `hx-get` section — safe to add now that `advisor:feed_partial` exists)
- `advisor/tests/test_views.py`

## Classes & Functions
`advisor/views.py`:
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
            pass
    return feed_partial(request)
```

## Task Breakdown
1. Write `advisor/views.py` exactly as above
2. Write `advisor/urls.py` — `app_name = "advisor"`, `path("feed/", views.feed_partial, name="feed_partial")`, `path("refresh/", views.refresh_insights, name="refresh")`
3. Confirm `config/urls.py` includes `advisor.urls`
4. Write `templates/partials/_advisor_feed.html`: wraps everything in `<div id="advisor-feed">`; a button `hx-post="{% url 'advisor:refresh' %}" hx-target="#advisor-feed" hx-swap="outerHTML" hx-indicator="#advisor-spinner"`; a hidden `<span id="advisor-spinner" class="htmx-indicator">Thinking…</span>`; then a card per insight showing `insight.summary` and, for each related `advice`, `advice.body`
5. Edit `templates/dashboard/dashboard.html`: add `<div hx-get="{% url 'advisor:feed_partial' %}" hx-trigger="load"></div>`
6. Write `advisor/tests/test_views.py`

## Testing Plan
Mock Ollama via `responses` in every test that could trigger a real AI call.

`advisor/tests/test_views.py`:
- `test_feed_partial_requires_login`
- `test_feed_partial_shows_recent_insights_with_advice` — create an `Insight` + related `AdviceMessage` via factories, GET `feed_partial`, assert both the insight's `summary` and the advice `body` appear in the response
- `test_feed_partial_limits_to_10` — create 12 insights, assert exactly 10 appear
- `test_refresh_insights_creates_new_insights_and_advice` — set up an over-budget scenario (real data, exercising the actual rule from Sprint 10), mock the Ollama endpoint to return valid advice text, POST to `refresh`, assert a new `Insight` and its `AdviceMessage` both exist and appear in the response
- `test_refresh_insights_survives_ai_failure` — same over-budget setup, mock Ollama to return a 500, POST to `refresh`, assert the response is still 200 (not a 500 itself), the `Insight` was still created, and no `AdviceMessage` exists for it — proving the try/except boundary works

## Load & Scale
- The `hx-indicator` spinner is the entire mitigation for perceived latency in v1 — deliberately not more than that, per the synchronous-call decision above.
- `refresh_insights` recomputes all rules for the current month from scratch on every call — no incremental/delta computation. Acceptable given Sprint 10's load analysis already established the query cost is small (tens of queries, not hundreds); not optimized further here.

## Definition of Done
- All 5 tests pass
- With Ollama running locally: clicking "Refresh insights" in the browser produces new cards with real AI-generated commentary within a few seconds, and those insights are still visible on the next dashboard visit without clicking refresh again
