"""Negative-path integration tests: auth failures (bad/expired/forged JWTs)
and RBAC boundaries (a role must never see, or get data back from, another
role's exclusive resources — even when it explicitly asks). Auth tests decode
locally (see agentic_core.services.auth_service) and need no running stack;
RBAC tests run the real compiled graph, same as test_smart_search.py.
"""

import time

import jwt
import pytest

from agentic_core.configs.config import settings
from agentic_core.graph import graph
from agentic_core.services.auth_service import build_initial_state
from agentic_core.state.state import State

# Resources every non-manager catalog must never contain, regardless of what
# the prompt asks for — the catalog is role-filtered before planning even
# sees the query (see planning_service.build_catalog), so these should be
# structurally absent, not just unanswered.
MANAGER_ONLY_RAG_RESOURCES = {"legal_policies.md", "financial_policies.md"}
MANAGER_ONLY_API_RESOURCES = {
    "customer:GET /users",
    "customer:GET /addresses",
    "customer:GET /payment-methods",
    "operations:GET /orders",
    "operations:GET /payments",
    "operations:GET /invoices",
    "operations:GET /deliveries",
    "operations:GET /order-products",
}


def _make_token(role: str = "manager", exp_delta: int = 3600, secret: str | None = None) -> str:
    payload = {"sub": "test-user", "role": role, "exp": int(time.time()) + exp_delta}
    return jwt.encode(payload, secret or settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


class TestAuthFailures:
    def test_missing_authorization_header_rejected(self):
        with pytest.raises(Exception):
            build_initial_state(query="anything", authorization_header="", debug=False)

    def test_garbage_token_rejected(self):
        with pytest.raises(jwt.exceptions.InvalidTokenError):
            build_initial_state(query="anything", authorization_header="Bearer not-a-real-token", debug=False)

    def test_expired_token_rejected(self):
        expired = _make_token(exp_delta=-3600)
        with pytest.raises(jwt.exceptions.ExpiredSignatureError):
            build_initial_state(query="anything", authorization_header=f"Bearer {expired}", debug=False)

    def test_wrong_signature_rejected(self):
        forged = _make_token(secret="not-the-real-secret")
        with pytest.raises(jwt.exceptions.InvalidSignatureError):
            build_initial_state(query="anything", authorization_header=f"Bearer {forged}", debug=False)

    def test_missing_role_claim_rejected(self):
        no_role = jwt.encode(
            {"sub": "test-user", "exp": int(time.time()) + 3600},
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
        with pytest.raises(KeyError):
            build_initial_state(query="anything", authorization_header=f"Bearer {no_role}", debug=False)


class TestRbacBoundaries:
    @pytest.mark.parametrize("role", ["customer", "worker"])
    async def test_role_never_sees_manager_only_resources(self, auth_tokens, role):
        identity = auth_tokens[role]
        prompt = "What are our special pricing rules, and what do the legal policies say about refunds?"
        state = build_initial_state(query=prompt, authorization_header=f"Bearer {identity['token']}", debug=False)
        result = await graph.ainvoke(state)
        output = State(**result).model_dump(mode="json", exclude={"authorization_header"})

        resource_ids = {entry["resource_id"] for entry in output["catalog"]}
        assert all(entry["source"] != "sql" for entry in output["catalog"])
        assert not (resource_ids & MANAGER_ONLY_RAG_RESOURCES)
        assert not (resource_ids & MANAGER_ONLY_API_RESOURCES)
        assert isinstance(output["answer"], str) and output["answer"].strip()

    async def test_customer_never_sees_worker_only_resources(self, auth_tokens):
        identity = auth_tokens["customer"]
        prompt = "How do I process a return, and what's the SOP for handling a backorder?"
        state = build_initial_state(query=prompt, authorization_header=f"Bearer {identity['token']}", debug=False)
        result = await graph.ainvoke(state)
        output = State(**result).model_dump(mode="json", exclude={"authorization_header"})

        resource_ids = {entry["resource_id"] for entry in output["catalog"]}
        assert "order_processing_sop.md" not in resource_ids
        assert "customer_support_sop.md" not in resource_ids
        assert isinstance(output["answer"], str) and output["answer"].strip()
