"""Drives the compiled graph with astream(..., subgraphs=True) so callers get
a callback per step as it completes — including steps nested inside
orchestrator_node's per-branch dispatch subgraph and branch_node's per-branch
retry-loop subgraph (see their config forwarding) — instead of waiting for
the single final ainvoke result.
"""

import asyncio
import threading
from typing import Callable

from agentic_core.graph import graph
from agentic_core.services.auth_service import build_initial_state
from agentic_core.state.models.plan_models import StepResult

OnUpdate = Callable[[dict], None]

# The planning/guardrail/synthesis LLM clients are lru_cache'd singletons
# (see guardrail_service/planning_service/synthesis_node) whose async httpx
# connections bind to whichever event loop is running the first time they're
# used, so a fresh asyncio.run() loop per call breaks them with "Event loop
# is closed" on the second query — this loop is kept open for the process's
# lifetime instead. Streamlit runs different sessions' script reruns on
# different worker threads, and asyncio loops aren't safe to drive from two
# threads at once, so _loop_lock serializes access — a second concurrent
# query waits its turn rather than corrupting the shared loop (the likely
# cause of "stuck until page reload": two reruns racing on run_until_complete
# leaves the loop in a broken state with no way for either to recover).
_loop: asyncio.AbstractEventLoop | None = None
_loop_lock = threading.Lock()


def _get_loop() -> asyncio.AbstractEventLoop:
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
    return _loop


async def _consume(query: str, token: str, debug: bool, on_update: OnUpdate) -> dict:
    state = build_initial_state(query=query, authorization_header=f"Bearer {token}", debug=debug)
    accumulated: dict = {
        "query": query,
        "role": state.role,
        "authorization_header": state.authorization_header,
        "debug": debug,
        "step_results": {},
        "branches": {},
        "trace": [],
        "answer": "",
        "guardrail_passed": False,
    }

    async for _namespace, chunk in graph.astream(state, {}, stream_mode="updates", subgraphs=True):
        if not isinstance(chunk, dict):
            continue
        for update in chunk.values():
            if not isinstance(update, dict):
                continue
            if "step_results" in update:
                new_results: dict[str, StepResult] = update["step_results"]
                accumulated["step_results"].update(new_results)
            if "branches" in update:
                # Keyed by branch_id, like step_results — a branch's own
                # retry loop writes its entry more than once as its
                # approach's status/steps evolve, so this is a replace-by-key
                # merge (dict.update), not an append.
                accumulated["branches"].update(update["branches"])
            if update.get("trace"):
                accumulated["trace"].extend(update["trace"])
            if update.get("answer"):
                accumulated["answer"] = update["answer"]
            if "guardrail_passed" in update:
                accumulated["guardrail_passed"] = update["guardrail_passed"]
            on_update(accumulated)

    return accumulated


def run_query(query: str, token: str, debug: bool, on_update: OnUpdate) -> dict:
    """Synchronous entrypoint for Streamlit's script-per-run model: blocks
    until the graph finishes, calling on_update after every step so the
    caller can redraw the stepper incrementally within the same script run."""
    with _loop_lock:
        loop = _get_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_consume(query, token, debug, on_update))
