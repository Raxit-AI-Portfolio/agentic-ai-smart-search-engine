from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agentic_core.nodes.step_graph import build_step_graph
from agentic_core.routes.branch_retry_routing import route_after_evaluate
from agentic_core.services import evaluation_service, planning_service
from agentic_core.state.state import State


async def execute_approach(state: State, config: RunnableConfig) -> dict:
    branch = state.branches[state.active_branch_id]
    approach = branch.approaches[state.attempt_index]

    # Never mutate the shared Branch/Approach objects in place — each branch
    # runs on its own state copy (see orchestrator_node), but that copy is a
    # *shallow* model_copy, so the nested Branch/Approach instances are still
    # shared with the top-level state and any sibling branch running
    # concurrently unless every update goes through model_copy(update=...).
    running_approach = approach.model_copy(update={"status": "running"})
    updated_branch = branch.model_copy(
        update={"approaches": [running_approach if a.rank == approach.rank else a for a in branch.approaches]}
    )

    if not approach.steps:
        # validate_plan can filter every step out (none of them mapped to an
        # in-catalog resource) — build_step_graph can't compile a StateGraph
        # with no nodes, and there's nothing to run anyway; evaluate_approach
        # correctly reads an empty result set as an immediate failure.
        return {
            "branches": {branch.branch_id: updated_branch},
            "trace": [f"branch {branch.branch_id} approach {approach.rank}: no valid steps to run"],
        }

    step_graph = build_step_graph(approach.steps)
    # Reset trace/step_results for the nested per-approach step subgraph:
    # refs within this approach only ever resolve within it (see
    # execution_service.step_result_key), and resetting trace avoids the
    # nested run re-appending everything already accumulated at the branch
    # level (it shares State, including the trace reducer).
    subgraph_input = state.model_copy(update={"trace": [], "step_results": {}})
    result = await step_graph.ainvoke(subgraph_input, config)

    return {
        "step_results": result["step_results"],
        "trace": result["trace"],
        "branches": {branch.branch_id: updated_branch},
    }


async def evaluate_approach(state: State) -> dict:
    branch = state.branches[state.active_branch_id]
    approach = branch.approaches[state.attempt_index]
    approach_results = [
        result
        for result in state.step_results.values()
        if result.branch_id == branch.branch_id and result.approach_rank == approach.rank
    ]

    succeeded, failure_reason = await evaluation_service.evaluate_approach(branch, approach, approach_results)

    updated_approach = approach.model_copy(
        update={"status": "succeeded" if succeeded else "failed", "failure_reason": failure_reason}
    )
    updated_branch = branch.model_copy(
        update={"approaches": [updated_approach if a.rank == approach.rank else a for a in branch.approaches]}
    )
    trace_msg = (
        f"branch {branch.branch_id} approach {approach.rank}: succeeded"
        if succeeded
        else f"branch {branch.branch_id} approach {approach.rank}: failed — {failure_reason}"
    )
    return {"branches": {branch.branch_id: updated_branch}, "trace": [trace_msg]}


async def refine_approach(state: State) -> dict:
    branch = state.branches[state.active_branch_id]
    current_approach = branch.approaches[state.attempt_index]
    next_index = state.attempt_index + 1
    next_approach = branch.approaches[next_index]

    steps = planning_service.refine_approach(
        branch, next_approach.rank, current_approach.failure_reason or "", state.catalog
    )

    updated_next_approach = next_approach.model_copy(update={"steps": steps})
    updated_branch = branch.model_copy(
        update={"approaches": [updated_next_approach if a.rank == next_approach.rank else a for a in branch.approaches]}
    )
    trace_msg = f"branch {branch.branch_id}: refining approach {next_approach.rank} after rank {current_approach.rank} failure"
    return {"branches": {branch.branch_id: updated_branch}, "attempt_index": next_index, "trace": [trace_msg]}


def _build_branch_graph() -> CompiledStateGraph:
    """The branch retry loop's shape never changes per branch/query (unlike
    the per-approach step graph or the per-query branch fan-out), so it's
    compiled once here rather than rebuilt dynamically:
        START -> execute_approach -> evaluate_approach
                                          |-- succeeded / exhausted -> END
                                          `-- retry -> refine_approach -> execute_approach (loop)
    """
    builder = StateGraph(State)
    builder.add_node("execute_approach", execute_approach)
    builder.add_node("evaluate_approach", evaluate_approach)
    builder.add_node("refine_approach", refine_approach)

    builder.add_edge(START, "execute_approach")
    builder.add_edge("execute_approach", "evaluate_approach")
    builder.add_conditional_edges("evaluate_approach", route_after_evaluate, ["refine_approach", END])
    builder.add_edge("refine_approach", "execute_approach")

    return builder.compile()


branch_graph = _build_branch_graph()
