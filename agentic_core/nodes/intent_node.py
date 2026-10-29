from agentic_core.services.planning_service import build_catalog
from agentic_core.state.state import State


async def intent_node(state: State) -> dict:
    catalog = await build_catalog(state.role)
    return {
        "catalog": catalog,
        "trace": [f"intent: {len(catalog)} resource(s) available to role={state.role}"],
    }
