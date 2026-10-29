from agentic_core.services import rag_service
from agentic_core.services.execution_service import missing_refs, missing_refs_error, resolve_step_inputs, step_result_key
from agentic_core.state.models.plan_models import PlanStep, StepResult
from agentic_core.state.state import State


def _build_query(step: PlanStep, inputs: dict) -> str:
    if not inputs:
        return step.description
    context = ", ".join(f"{name}={value}" for name, value in inputs.items())
    return f"{step.description} ({context})"


async def rag_node(state: State, *, step: PlanStep) -> dict:
    key = step_result_key(step.branch_id, step.approach_rank, step.step_id)
    missing = missing_refs(step, state.step_results)
    if missing:
        step_result = missing_refs_error(step, missing)
        return {"step_results": {key: step_result}, "trace": [f"rag[{step.step_id}]: skipped — {step_result.error}"]}

    inputs = resolve_step_inputs(step, state.step_results)
    query = _build_query(step, inputs)

    try:
        chunks = rag_service.search(query, state.role, source_file=step.resource)
    except Exception as exc:
        step_result = StepResult(
            step_id=step.step_id,
            branch_id=step.branch_id,
            approach_rank=step.approach_rank,
            source=step.source,
            resource=step.resource,
            description=step.description,
            inputs=inputs,
            error=str(exc),
        )
        return {"step_results": {key: step_result}, "trace": [f"rag[{step.step_id}]: error — {exc}"]}

    step_result = StepResult(
        step_id=step.step_id,
        branch_id=step.branch_id,
        approach_rank=step.approach_rank,
        source=step.source,
        resource=step.resource,
        description=step.description,
        inputs=inputs,
        operation_summary=f"Retrieved {len(chunks)} chunk(s) from {step.resource}",
        output=[chunk.model_dump() for chunk in chunks],
    )
    trace_msg = f"rag[{step.step_id}]: {len(chunks)} chunk(s) from {step.resource}"
    return {"step_results": {key: step_result}, "trace": [trace_msg]}
