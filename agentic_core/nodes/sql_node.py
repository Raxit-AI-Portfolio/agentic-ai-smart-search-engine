from agentic_core.services import sql_service
from agentic_core.services.execution_service import missing_refs, missing_refs_error, resolve_step_inputs, step_result_key
from agentic_core.state.models.plan_models import PlanStep, StepResult, StepTable
from agentic_core.state.state import State


async def sql_node(state: State, *, step: PlanStep) -> dict:
    key = step_result_key(step.branch_id, step.approach_rank, step.step_id)
    missing = missing_refs(step, state.step_results)
    if missing:
        step_result = missing_refs_error(step, missing)
        return {"step_results": {key: step_result}, "trace": [f"sql[{step.step_id}]: skipped — {step_result.error}"]}

    inputs = resolve_step_inputs(step, state.step_results)
    resource_description = next(
        (entry.description for entry in state.catalog if entry.source == "sql" and entry.resource_id == step.resource),
        "",
    )
    result = await sql_service.run_text_to_sql(step.resource, step.description, inputs, resource_description)

    output_table = (
        StepTable(columns=list(result.rows[0].keys()), rows=[list(row.values()) for row in result.rows])
        if result.rows
        else None
    )
    retry_note = f" after {result.retries} retry(ies)" if result.retries else ""
    step_result = StepResult(
        step_id=step.step_id,
        branch_id=step.branch_id,
        approach_rank=step.approach_rank,
        source=step.source,
        resource=step.resource,
        description=step.description,
        inputs=inputs,
        operation_summary=None if result.error else f"Fetched {len(result.rows)} row(s) from {step.resource}{retry_note}",
        output=result.rows,
        output_table=output_table,
        error=result.error,
    )
    trace_msg = (
        f"sql[{step.step_id}]: error — {result.error}"
        if result.error
        else f"sql[{step.step_id}]: {len(result.rows)} row(s) from {step.resource}{retry_note}"
    )
    return {"step_results": {key: step_result}, "trace": [trace_msg]}
