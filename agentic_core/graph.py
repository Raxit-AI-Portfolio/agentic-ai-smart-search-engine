from langgraph.graph import END, START, StateGraph

from agentic_core.nodes.guardrail_node import guardrail_node
from agentic_core.nodes.intent_node import intent_node
from agentic_core.nodes.orchestrator_node import orchestrator_node
from agentic_core.nodes.planning_node import planning_node
from agentic_core.nodes.synthesis_node import synthesis_node
from agentic_core.routes.guardrail_routing import route_after_guardrail
from agentic_core.state.state import State

builder = StateGraph(State)

builder.add_node("guardrail_node", guardrail_node)
builder.add_node("intent_node", intent_node)
builder.add_node("planning_node", planning_node)
builder.add_node("orchestrator_node", orchestrator_node)
builder.add_node("synthesis_node", synthesis_node)

builder.add_edge(START, "guardrail_node")
builder.add_conditional_edges("guardrail_node", route_after_guardrail, ["intent_node", END])
builder.add_edge("intent_node", "planning_node")
builder.add_edge("planning_node", "orchestrator_node")
builder.add_edge("orchestrator_node", "synthesis_node")
builder.add_edge("synthesis_node", END)

# Every node here is async (the underlying services use asyncpg/httpx/redis.asyncio),
# so the compiled graph must be run via ainvoke/astream, not invoke/stream.
graph = builder.compile()
