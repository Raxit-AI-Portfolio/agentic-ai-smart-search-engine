from typing import Literal

from agentic_core.state.state import State


def route_after_evaluate(state: State) -> Literal["refine_approach", "__end__"]:
    branch = state.branches[state.active_branch_id]
    current = branch.approaches[state.attempt_index]
    if current.status == "succeeded":
        return "__end__"
    has_next_approach = state.attempt_index + 1 < len(branch.approaches)
    return "refine_approach" if has_next_approach else "__end__"
