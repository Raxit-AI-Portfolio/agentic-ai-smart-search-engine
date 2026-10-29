from agentic_core.services.planning_service import decompose_query, validate_plan
from agentic_core.state.state import State


async def planning_node(state: State) -> dict:
    # A branch with zero approaches has nothing for orchestrator_node/
    # branch_node to dispatch (approaches[0] would just IndexError) — drop it
    # rather than pass it through.
    branches = [branch for branch in decompose_query(state.query, state.catalog) if branch.approaches]

    trace = [f"planning: {len(branches)} branch(es)"]
    for branch in branches:
        rank1 = branch.approaches[0]
        rank1.steps = validate_plan(rank1.steps, state.catalog)
        trace.append(
            f"branch {branch.branch_id} ({branch.sub_query}): {len(branch.approaches)} approach(es), "
            f"trying rank {rank1.rank} [{rank1.strategy}] (confidence {rank1.confidence:.2f})"
        )
        trace += [
            f"  step {step.step_id} -> [{step.source}] {step.resource}"
            + (f" (depends on {', '.join(step.depends_on)})" if step.depends_on else "")
            for step in rank1.steps
        ]

    return {"branches": {branch.branch_id: branch for branch in branches}, "trace": trace}
