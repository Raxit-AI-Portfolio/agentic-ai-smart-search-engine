from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from agentic_core.configs.config import settings
from agentic_core.prompts.evaluation_prompts import EVALUATION_SYSTEM_PROMPT, build_evaluation_prompt
from agentic_core.state.models.plan_models import Approach, Branch, StepResult


class _Verdict(BaseModel):
    sufficient: bool
    reason: str = Field(
        default="",
        description="If not sufficient, a short concrete explanation of what's missing or wrong — fed to the next approach as failure context.",
    )


@lru_cache
def _judge() -> ChatGoogleGenerativeAI:
    llm = ChatGoogleGenerativeAI(model=settings.planning_model, google_api_key=settings.google_api_key)
    return llm.with_structured_output(_Verdict)


def _is_unusable(result: StepResult) -> bool:
    return result.error is not None or not result.output


async def evaluate_approach(branch: Branch, approach: Approach, approach_results: list[StepResult]) -> tuple[bool, str | None]:
    """Two-tier check, cheapest first:
    1. Code-only: every step for this approach errored or returned nothing
       usable -> obviously failed, no LLM call needed.
    2. Otherwise (at least one step returned data): one LLM call judges
       whether the collected data actually answers the branch's sub-query.
    Returns (succeeded, failure_reason) — failure_reason is None on success.
    """
    if not approach_results or all(_is_unusable(result) for result in approach_results):
        errors = [result.error for result in approach_results if result.error]
        reason = "; ".join(errors) if errors else "no step produced usable output"
        return False, reason

    prompt = build_evaluation_prompt(branch, approach, approach_results)
    verdict = await _judge().ainvoke([("system", EVALUATION_SYSTEM_PROMPT), ("human", prompt)])
    return verdict.sufficient, (None if verdict.sufficient else (verdict.reason or "results judged insufficient"))
