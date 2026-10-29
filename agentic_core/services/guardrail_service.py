from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from agentic_core.configs.config import settings
from agentic_core.prompts.guardrail_prompts import GUARDRAIL_SYSTEM_PROMPT, build_guardrail_prompt


class GuardrailVerdict(BaseModel):
    allowed: bool
    reason: str | None = None


@lru_cache
def _guardrail() -> ChatGoogleGenerativeAI:
    llm = ChatGoogleGenerativeAI(model=settings.planning_model, google_api_key=settings.google_api_key)
    return llm.with_structured_output(GuardrailVerdict)


async def check_query(query: str) -> GuardrailVerdict:
    if not query or not query.strip():
        return GuardrailVerdict(allowed=False, reason="Please enter a question.")
    prompt = build_guardrail_prompt(query)
    return await _guardrail().ainvoke([("system", GUARDRAIL_SYSTEM_PROMPT), ("human", prompt)])
