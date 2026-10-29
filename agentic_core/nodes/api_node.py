import asyncio
import re

import httpx

from agentic_core.services import api_service
from agentic_core.services.execution_service import missing_refs, missing_refs_error, resolve_step_inputs, step_result_key
from agentic_core.state.models.plan_models import PlanStep, StepResult
from agentic_core.state.state import State

_PATH_PARAM = re.compile(r"\{(\w+)\}")

# Per-row fan-out issues one real API call per value; past this the result is
# an unbounded burst against the backend, so fail rather than truncate silently.
MAX_FANOUT = 25


class _FanoutError(ValueError):
    """A ref resolved to multiple rows but fan-out can't cover it (more than
    one list-valued path param, or more rows than MAX_FANOUT)."""


def _expand_paths(path: str, inputs: dict) -> tuple[list[str], dict]:
    """Fills {param} placeholders from inputs. If exactly one path param is a
    multi-row list, returns one resolved path per value (per-row fan-out);
    otherwise a single path. Second item is the inputs left for the
    query/body."""
    path_names = set(_PATH_PARAM.findall(path))
    leftover = {k: v for k, v in inputs.items() if k not in path_names}
    list_names = [n for n in path_names if isinstance(inputs.get(n), list)]
    if len(list_names) > 1:
        raise _FanoutError(f"path params {sorted(list_names)} each resolved to multiple values; only one can fan out")
    fan = list_names[0] if list_names else None
    values = list(dict.fromkeys(inputs[fan])) if fan else [None]
    if len(values) > MAX_FANOUT:
        raise _FanoutError(f"'{fan}' resolved to {len(values)} values, over the fan-out limit of {MAX_FANOUT}")

    def _fill(fan_value: object) -> str:
        def _sub(match: re.Match) -> str:
            name = match.group(1)
            if name == fan:
                return str(fan_value)
            return str(inputs[name]) if name in inputs else match.group(0)

        return _PATH_PARAM.sub(_sub, path)

    return [_fill(v) for v in values], leftover


def _describe_error(exc: Exception, path: str) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code == 404:
            return f"not found: no record exists for {path}"
        if code in (400, 422):
            return f"invalid input: the API rejected {path} ({code}) — an ID or value is malformed"
    return str(exc)


async def api_node(state: State, *, step: PlanStep) -> dict:
    key = step_result_key(step.branch_id, step.approach_rank, step.step_id)
    missing = missing_refs(step, state.step_results)
    if missing:
        step_result = missing_refs_error(step, missing)
        return {"step_results": {key: step_result}, "trace": [f"api[{step.step_id}]: skipped — {step_result.error}"]}

    inputs = resolve_step_inputs(step, state.step_results)
    service, _, method_path = step.resource.partition(":")
    method, path = method_path.split(" ", 1)

    resolved_path = path
    try:
        paths, remaining_inputs = _expand_paths(path, inputs)
        outcomes = await asyncio.gather(
            *(
                api_service.call_api(
                    service,
                    method,
                    p,
                    state.authorization_header,
                    params=remaining_inputs if method.upper() == "GET" else None,
                    json=remaining_inputs if method.upper() != "GET" else None,
                )
                for p in paths
            ),
            return_exceptions=True,
        )
        failures = [(p, o) for p, o in zip(paths, outcomes) if isinstance(o, Exception)]
        if len(failures) == len(paths):
            failed_path, failure = failures[0]
            raise RuntimeError(_describe_error(failure, failed_path)) from failure
        successes = [o for o in outcomes if not isinstance(o, Exception)]
        resolved_path = paths[0] if len(paths) == 1 else f"{path} x{len(paths)}"
        if len(paths) == 1:
            payload = successes[0]
        else:
            payload = [row for o in successes for row in (o if isinstance(o, list) else [o])]
    except (_FanoutError, RuntimeError) as exc:
        error = str(exc)
    except Exception as exc:
        error = _describe_error(exc, path)
    else:
        error = None

    if error is not None:
        step_result = StepResult(
            step_id=step.step_id,
            branch_id=step.branch_id,
            approach_rank=step.approach_rank,
            source=step.source,
            resource=step.resource,
            description=step.description,
            inputs=inputs,
            error=error,
        )
        return {"step_results": {key: step_result}, "trace": [f"api[{step.step_id}]: error — {error}"]}

    step_result = StepResult(
        step_id=step.step_id,
        branch_id=step.branch_id,
        approach_rank=step.approach_rank,
        source=step.source,
        resource=step.resource,
        description=step.description,
        inputs=inputs,
        operation_summary=f"Called {method} {resolved_path} on {service}-api",
        output=payload,
    )
    trace_msg = f"api[{step.step_id}]: {method} {resolved_path} ({service}-api) -> ok"
    return {"step_results": {key: step_result}, "trace": [trace_msg]}
