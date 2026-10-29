from agentic_core.services.guardrail_service import check_query
from agentic_core.state.state import State


async def guardrail_node(state: State) -> dict:
    verdict = await check_query(state.query)
    if verdict.allowed:
        return {"guardrail_passed": True, "trace": ["guardrail: passed"]}

    return {
        "guardrail_passed": False,
        "answer": verdict.reason or "I can't help with that request.",
        "trace": [f"guardrail: rejected — {verdict.reason}"],
    }
