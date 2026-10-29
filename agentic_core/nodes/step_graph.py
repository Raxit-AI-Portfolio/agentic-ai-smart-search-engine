from functools import partial

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agentic_core.nodes.api_node import api_node
from agentic_core.nodes.rag_node import rag_node
from agentic_core.nodes.sql_node import sql_node
from agentic_core.state.models.plan_models import PlanStep
from agentic_core.state.state import State

_NODE_BY_SOURCE = {"sql": sql_node, "rag": rag_node, "api": api_node}


def build_step_graph(steps: list[PlanStep]) -> CompiledStateGraph:
    """Builds a fresh StateGraph for one approach's steps: one node per step
    (bound to its worker via functools.partial) with edges from
    step.depends_on. LangGraph's normal fan-in (a node runs once all its
    predecessors finish) gives dependency-ordered, concurrent-where-possible
    execution for free — no custom scheduler needed. Used by
    branch_node.execute_approach."""
    builder = StateGraph(State)
    is_a_dependency = dict.fromkeys((step.step_id for step in steps), False)

    for step in steps:
        builder.add_node(step.step_id, partial(_NODE_BY_SOURCE[step.source], step=step))
        if step.depends_on:
            for dep_id in step.depends_on:
                builder.add_edge(dep_id, step.step_id)
                is_a_dependency[dep_id] = True
        else:
            builder.add_edge(START, step.step_id)

    for step_id, has_dependents in is_a_dependency.items():
        if not has_dependents:
            builder.add_edge(step_id, END)

    return builder.compile()
