import json
import re

from agentic_core.graph import graph
from agentic_core.services.auth_service import build_initial_state
from agentic_core.state.state import State

from tests.integration_tests.conftest import RESULTS_DIR


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug[:60]


async def run_scenario(*, username: str, role: str, debug: bool, prompt: str, token: str) -> dict:
    """Builds the real initial State from a live JWT (see build_initial_state),
    runs it through the full compiled graph end-to-end, writes the input +
    JSON output to a result file for manual review, and returns the output
    dict so the caller can make its own (partial) assertions on it."""
    state = build_initial_state(query=prompt, authorization_header=f"Bearer {token}", debug=debug)
    result = await graph.ainvoke(state)

    final_state = State(**result)
    output = final_state.model_dump(mode="json", exclude={"authorization_header"})

    lines = [
        "Input:",
        f"username: {username}",
        f"role: {role}",
        f"debug mode: {debug}",
        f"prompt: {prompt}",
        "",
        "Output:",
        json.dumps(output, indent=2, default=str),
    ]
    filename = f"{role}_{'debug' if debug else 'nodebug'}_{_slugify(prompt)}.txt"
    (RESULTS_DIR / filename).write_text("\n".join(lines), encoding="utf-8")

    return output
