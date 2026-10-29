from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI

from agentic_core.configs.config import settings
from agentic_core.prompts.synthesis_prompts import SYNTHESIS_SYSTEM_PROMPT, build_synthesis_prompt
from agentic_core.state.models.plan_models import Branch, StepResult
from agentic_core.state.state import State


@lru_cache
def _synthesizer() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=settings.planning_model, google_api_key=settings.google_api_key)


def _winning_results_by_branch(state: State) -> tuple[list[Branch], dict[str, list[StepResult]]]:
    """One approach's results per branch — never a mix of an earlier failed
    attempt's data alongside the one that actually succeeded. Prefers the
    succeeded approach; if a branch exhausted every approach without one,
    falls back to its last-attempted approach so the answer can still say
    "couldn't fully answer this part" using whatever partial data exists.
    Branches are returned in state.branches' own order (== the plan's
    original branch order, itself following the user's question) so
    synthesis can be told to answer in that same order instead of whatever
    order the LLM feels like."""
    ordered_branches = []
    results_by_branch: dict[str, list[StepResult]] = {}

    for branch in state.branches.values():
        tried = [a for a in branch.approaches if a.status in ("succeeded", "failed")]
        if not tried:
            continue
        chosen = next((a for a in tried if a.status == "succeeded"), tried[-1])
        ordered_branches.append(branch)
        results_by_branch[branch.branch_id] = [
            result
            for result in state.step_results.values()
            if result.branch_id == branch.branch_id and result.approach_rank == chosen.rank
        ]

    return ordered_branches, results_by_branch


async def synthesis_node(state: State) -> dict:
    branches, results_by_branch = _winning_results_by_branch(state)
    total_results = sum(len(results) for results in results_by_branch.values())
    if not branches or not total_results:
        return {"trace": ["synthesis: no step results to synthesize"], "answer": "I couldn't find anything to answer that."}

    prompt = build_synthesis_prompt(state.query, branches, results_by_branch, state.debug)
    response = await _synthesizer().ainvoke([("system", SYNTHESIS_SYSTEM_PROMPT), ("human", prompt)])

    return {
        "trace": [f"synthesis: generated answer from {total_results} step result(s) across {len(branches)} branch(es)"],
        "answer": response.content,
    }
