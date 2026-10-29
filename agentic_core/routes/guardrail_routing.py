from typing import Literal

from agentic_core.state.state import State


def route_after_guardrail(state: State) -> Literal["intent_node", "__end__"]:
    return "intent_node" if state.guardrail_passed else "__end__"
