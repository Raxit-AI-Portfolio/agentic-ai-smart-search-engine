"""End-to-end integration tests for the compiled LangGraph: real Postgres
(SQL MCP path), real Qdrant + BM25 (RAG path), real customer-api/operations-api
(API path), and the real Gemini planning/synthesis LLM calls.

Requires the full stack up (docker compose, seeded databases, ingested RAG
docs) and a real GOOGLE_API_KEY in .env — see the README
deployment notes. Each scenario's full JSON output is written to
tests/integration_tests/results/ for manual review; assertions here are
intentionally light (structural/RBAC invariants) rather than exact-answer
checks, since the plan/answer come from a live LLM and will vary run to run.
"""

import pytest

from tests.integration_tests.helpers import run_scenario

CUSTOMER_PROMPTS = [
    "What is our return policy for damaged items?",
    # Deliberately gives the order id rather than "my most recent order" — no
    # customer-facing endpoint can resolve "most recent" from identity alone
    # yet, so that phrasing has no valid plan.
    "What's the status of order 1, and what payment method was used for it?",
]

WORKER_PROMPTS = [
    "How do I process a return for a customer?",
    "What's the current inventory for our products, and what's the SOP for handling a backorder?",
]

MANAGER_PROMPTS = [
    "Show me the total revenue by customer this month.",
    "What are our special pricing rules, and what do the legal policies say about refunds?",
]


@pytest.mark.parametrize("prompt", CUSTOMER_PROMPTS)
async def test_customer_scenarios(auth_tokens, prompt):
    identity = auth_tokens["customer"]
    output = await run_scenario(username=identity["username"], role="customer", debug=False, prompt=prompt, token=identity["token"])

    assert output["view_mode"] == "direct"
    assert isinstance(output["answer"], str) and output["answer"].strip()
    # RBAC invariant: customer role must never see an sql-source catalog entry.
    assert all(entry["source"] != "sql" for entry in output["catalog"])


@pytest.mark.parametrize("prompt", WORKER_PROMPTS)
async def test_worker_scenarios(auth_tokens, prompt):
    identity = auth_tokens["worker"]
    output = await run_scenario(username=identity["username"], role="worker", debug=False, prompt=prompt, token=identity["token"])

    assert output["view_mode"] == "stepper"
    assert isinstance(output["answer"], str) and output["answer"].strip()
    assert all(entry["source"] != "sql" for entry in output["catalog"])


@pytest.mark.parametrize("debug", [False, True])
@pytest.mark.parametrize("prompt", MANAGER_PROMPTS)
async def test_manager_scenarios(auth_tokens, prompt, debug):
    identity = auth_tokens["manager"]
    output = await run_scenario(username=identity["username"], role="manager", debug=debug, prompt=prompt, token=identity["token"])

    assert output["view_mode"] == ("stepper_debug" if debug else "stepper")
    assert isinstance(output["answer"], str) and output["answer"].strip()
    # Manager is the broadest role — its catalog should never come back empty
    # on a live, seeded stack.
    assert output["catalog"]
