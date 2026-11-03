from functools import partial

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agentic_core.nodes.branch_node import branch_graph
from agentic_core.state.state import State


async def _run_branch(state: State, config: RunnableConfig, *, branch_id: str) -> dict:
    subgraph_input = state.model_copy(
        update={"trace": [], "step_results": {}, "active_branch_id": branch_id, "attempt_index": 0}
    )
    result = await branch_graph.ainvoke(subgraph_input, config)
    # result["branches"] carries every branch's entry, not just this one —
    # the subgraph_input above deliberately keeps the full branches dict
    # (unmodified) so execute_approach/evaluate_approach/refine_approach can
    # look up *this* branch by id, but that means the OTHER branches' stale,
    # never-touched "pending" copies ride along in the result too. Branches
    # run concurrently, each contributing a full-width dict like this one —
    # returning it as-is would let whichever branch's update gets merged
    # last (via State.branches' operator.or_) silently stomp its siblings'
    # already-correct results back to "pending". Only ever return this
    # branch's own key.
    return {
        "step_results": result["step_results"],
        "trace": result["trace"],
        "branches": {branch_id: result["branches"][branch_id]},
    }


def _build_dispatch_graph(branch_ids: list[str]) -> CompiledStateGraph:
    """Branches are unrelated by definition (see planning_service.decompose_query),
    so one node per branch, all wired START->node->END, runs them concurrently —
    same fan-out pattern independent steps already use in step_graph.py."""
    builder = StateGraph(State)
    for branch_id in branch_ids:
        builder.add_node(branch_id, partial(_run_branch, branch_id=branch_id))
        builder.add_edge(START, branch_id)
        builder.add_edge(branch_id, END)
    return builder.compile()


async def orchestrator_node(state: State, config: RunnableConfig) -> dict:
    if not state.branches:
        return {"trace": ["orchestrator: no branches to execute"]}

    dispatch_graph = _build_dispatch_graph(list(state.branches.keys()))
    # Clean trace for the dispatch subgraph, same reasoning as branch_node's
    # own nested step_graph reset: this shares State (incl. the trace
    # reducer) with the parent, so without this it would re-append
    # everything already in state.trace when folded back below.
    subgraph_input = state.model_copy(update={"trace": []})
    result = await dispatch_graph.ainvoke(subgraph_input, config)

    return {"step_results": result["step_results"], "trace": result["trace"], "branches": result["branches"]}
