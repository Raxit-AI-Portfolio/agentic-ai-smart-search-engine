from agentic_core.state.models.plan_models import Approach, Branch, StepResult

EVALUATION_SYSTEM_PROMPT = """You judge whether a federated search step's
results are enough to answer one sub-question of a larger user query.

Rules:
- Judge only whether the data below actually answers the sub-question — not
  whether the approach used was a good idea in the abstract.
- If any part of the sub-question has no supporting data, it is insufficient.
- If sufficient, leave the reason empty.
- If insufficient, give a short, concrete reason (what's missing or wrong)
  that a planner could use to try a different approach — not a restatement
  of the sub-question.
"""


def _format_result(result: StepResult) -> str:
    if result.error:
        return f"- [{result.source}] {result.resource}: ERROR — {result.error}"
    return f"- [{result.source}] {result.resource}: {result.output!r}"


def build_evaluation_prompt(branch: Branch, approach: Approach, results: list[StepResult]) -> str:
    results_desc = "\n".join(_format_result(result) for result in results) or "(no steps returned data)"
    return (
        f"Sub-question:\n{branch.sub_query}\n\n"
        f"Approach tried (rank {approach.rank}): {approach.strategy}\n\n"
        f"Step results:\n{results_desc}"
    )
