from typing import Any

from agentic_core.state.models.plan_models import PlanStep, StepResult


def step_result_key(branch_id: str, approach_rank: int, step_id: str) -> str:
    """step_results is keyed by this composite, not bare step_id — a
    refined/retried approach can reuse the same step_ids as the one it's
    replacing, and branches run concurrently, so bare step_id isn't unique
    across the whole run. A ref always resolves within the same approach, so
    the referencing step's own branch_id/approach_rank apply to the
    referenced step too."""
    return f"{branch_id}.{approach_rank}.{step_id}"


def _matching_key(name: str, keys: Any) -> str | None:
    if name in keys:
        return name
    stripped = name.removeprefix("p_")
    if stripped in keys:
        return stripped
    return None


def _extract_ref_value(name: str, output: Any, output_field: str | None) -> Any:
    """A ref names the param the dependent step needs (e.g. "p_invoice_id" or
    "payment_id"), not necessarily a field path into the upstream step's
    output — so, absent an explicit output_field (planning_service sets it
    when the upstream output is a multi-field dict and only one field is
    needed), pull the matching field out of it: one value from a
    single-object output (an API call), or one value per row from a list
    output (a SQL query) — except a single-row list, which unwraps to that
    one scalar rather than a one-element list, since a ref is normally
    consumed as a single value (e.g. an API path parameter) and only
    genuinely means "one per row" when there's more than one row."""
    if output_field:
        if isinstance(output, dict):
            return output.get(output_field)
        if isinstance(output, list) and output and isinstance(output[0], dict):
            values = [row.get(output_field) for row in output]
            return values[0] if len(values) == 1 else values
        return output
    if isinstance(output, dict):
        key = _matching_key(name, output.keys())
        return output[key] if key else output
    if isinstance(output, list) and output and isinstance(output[0], dict):
        key = _matching_key(name, output[0].keys())
        if not key:
            return output
        values = [row[key] for row in output]
        return values[0] if len(values) == 1 else values
    return output


def resolve_step_inputs(step: PlanStep, step_results: dict[str, StepResult]) -> dict[str, Any]:
    resolved: dict[str, Any] = {param.name: param.value for param in step.input_params}
    for ref in step.input_refs:
        key = step_result_key(step.branch_id, step.approach_rank, ref.ref_step_id)
        upstream = step_results.get(key)
        resolved[ref.name] = _extract_ref_value(ref.name, upstream.output, ref.output_field) if upstream else None
    return resolved


def missing_refs(step: PlanStep, step_results: dict[str, StepResult]) -> list[str]:
    """input_refs whose upstream step failed, is missing, or produced no
    output — resolve_step_inputs silently maps these to None, which would
    otherwise get sent to a real backend as the literal string "None" rather
    than failing the step outright."""
    missing = []
    for ref in step.input_refs:
        key = step_result_key(step.branch_id, step.approach_rank, ref.ref_step_id)
        upstream = step_results.get(key)
        if upstream is None or upstream.error is not None or upstream.output is None:
            missing.append(ref.name)
    return missing


def missing_refs_error(step: PlanStep, missing: list[str]) -> StepResult:
    return StepResult(
        step_id=step.step_id,
        branch_id=step.branch_id,
        approach_rank=step.approach_rank,
        source=step.source,
        resource=step.resource,
        description=step.description,
        inputs={},
        error=f"cannot run: required input(s) {', '.join(missing)} unavailable — an earlier step failed or returned no value",
    )
