from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from agentic_core.configs.config import settings
from agentic_core.prompts.intent_prompts import (
    PLANNING_SYSTEM_PROMPT,
    REFINE_SYSTEM_PROMPT,
    build_planning_prompt,
    build_refine_prompt,
)
from agentic_core.services import api_service, rag_service, sql_service
from agentic_core.state.models.plan_models import Branch, CatalogEntry, PlanStep, Source
from agentic_core.state.state import Role


async def build_catalog(role: Role) -> list[CatalogEntry]:
    sql_permissions = await sql_service.list_permissions()
    api_permissions = await api_service.list_permissions()
    rag_permissions = rag_service.list_permissions()

    permissions_by_source: dict[Source, dict[str, list[str]]] = {
        "sql": sql_permissions,
        "api": api_permissions,
        "rag": rag_permissions,
    }

    # Only describe what's actually role-filtered in below, not every object
    # in existence — descriptions live-introspect (sql) / read a Redis cache
    # (api), so there's no reason to fetch ones the caller can't use anyway.
    sql_descriptions = await sql_service.describe_objects()
    api_descriptions = await api_service.describe_objects()
    rag_descriptions = rag_service.describe_objects()
    descriptions_by_source: dict[Source, dict[str, str]] = {
        "sql": sql_descriptions,
        "api": api_descriptions,
        "rag": rag_descriptions,
    }

    entries = [
        CatalogEntry(source=source, resource_id=resource_id, description=descriptions_by_source[source].get(resource_id, ""))
        for source, permissions in permissions_by_source.items()
        for resource_id, allowed_roles in permissions.items()
        if role in allowed_roles
    ]
    # Deterministic ordering — otherwise within-source order follows whatever
    # Postgres/Redis/the RAG manifest happen to return it in, which drifts
    # run to run and makes the catalog harder to scan/diff.
    return sorted(entries, key=lambda entry: (entry.source, entry.resource_id))


class _DecomposedQuery(BaseModel):
    """LLM structured-output schema for decompose_query — a thin wrapper
    around Branch, kept private to this module (not a shared state model,
    same reasoning as evaluation_service._Verdict)."""

    branches: list[Branch] = Field(default_factory=list)


class _StepList(BaseModel):
    """LLM structured-output schema for refine_approach."""

    steps: list[PlanStep] = Field(default_factory=list)


@lru_cache
def _planner():
    llm = ChatGoogleGenerativeAI(model=settings.planning_model, google_api_key=settings.google_api_key)
    return llm.with_structured_output(_DecomposedQuery)


@lru_cache
def _refiner():
    llm = ChatGoogleGenerativeAI(model=settings.planning_model, google_api_key=settings.google_api_key)
    return llm.with_structured_output(_StepList)


def _stamp_steps(steps: list[PlanStep], branch_id: str, approach_rank: int) -> None:
    for step in steps:
        step.branch_id = branch_id
        step.approach_rank = approach_rank
        step.depends_on = sorted({ref.ref_step_id for ref in step.input_refs})


def decompose_query(query: str, catalog: list[CatalogEntry]) -> list[Branch]:
    prompt = build_planning_prompt(query, catalog)
    decomposed = _planner().invoke([("system", PLANNING_SYSTEM_PROMPT), ("human", prompt)])

    for branch in decomposed.branches:
        branch.approaches.sort(key=lambda approach: approach.rank)
        if branch.approaches:
            rank1 = branch.approaches[0]
            _stamp_steps(rank1.steps, branch.branch_id, rank1.rank)

    return decomposed.branches


def refine_approach(branch: Branch, next_rank: int, failure_reason: str, catalog: list[CatalogEntry]) -> list[PlanStep]:
    approach = next(a for a in branch.approaches if a.rank == next_rank)
    prompt = build_refine_prompt(branch, approach, failure_reason, catalog)
    refined = _refiner().invoke([("system", REFINE_SYSTEM_PROMPT), ("human", prompt)])
    _stamp_steps(refined.steps, branch.branch_id, next_rank)
    return validate_plan(refined.steps, catalog)


def validate_plan(steps: list[PlanStep], catalog: list[CatalogEntry]) -> list[PlanStep]:
    allowed = {(entry.source, entry.resource_id) for entry in catalog}
    kept: list[PlanStep] = [step for step in steps if (step.source, step.resource) in allowed]
    valid_ids = {step.step_id for step in kept}

    # Cascade-drop steps whose upstream dependency got rejected above — their
    # input_refs can no longer be resolved.
    changed = True
    while changed:
        changed = False
        for step in list(kept):
            if any(dep not in valid_ids for dep in step.depends_on):
                kept.remove(step)
                valid_ids.discard(step.step_id)
                changed = True

    return kept
