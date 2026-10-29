from typing import Any, Literal

from pydantic import BaseModel, Field

Source = Literal["sql", "rag", "api"]
ApproachStatus = Literal["pending", "running", "succeeded", "failed"]


class CatalogEntry(BaseModel):
    source: Source
    resource_id: str
    # What the resource does and, for sql, its real signature/columns — see
    # sql_service.describe_objects / api_service.describe_objects. Empty when
    # a source has no description available (currently: rag).
    description: str = ""


class ParamValue(BaseModel):
    name: str
    value: str


class ParamRef(BaseModel):
    name: str
    ref_step_id: str
    # Field to pull out of the upstream step's output when it's a dict with
    # more than one field (e.g. "payment_id" out of a full invoice object).
    # None when the upstream output is already the single value needed, or is
    # a list of rows — resolve_step_inputs falls back to its existing
    # name-matching extraction in that case.
    output_field: str | None = None


class PlanStep(BaseModel):
    step_id: str
    description: str
    source: Source
    resource: str
    # Literal values the step needs, known up front. list[ParamValue] rather
    # than dict[str, str] — Gemini structured output doesn't reliably support
    # arbitrary-key object schemas (additionalProperties).
    input_params: list[ParamValue] = Field(default_factory=list)
    # Values the step needs that come from another step's output instead.
    input_refs: list[ParamRef] = Field(default_factory=list)
    # Derived from input_refs by planning_service, not filled by the LLM —
    # keeping it a plain field (rather than a computed property) lets the
    # step-graph builder read it directly when wiring edges.
    depends_on: list[str] = Field(default_factory=list)
    # Stamped on by planning_service (decompose_query/refine_approach), not
    # filled by the LLM — lets step_results stay uniquely keyed across
    # branches and across an approach that gets retried under the same
    # step_id (see execution_service._key).
    branch_id: str = ""
    approach_rank: int = 1


class Approach(BaseModel):
    rank: int = Field(description="1, 2, or 3 — this approach's priority order within its branch.")
    strategy: str = Field(description="Short description of this approach's angle/resource — must genuinely differ from other ranks, not reorder/rephrase them.")
    confidence: float = Field(description="Self-rated 0-1 likelihood this approach fully answers the branch's sub_query.")
    steps: list[PlanStep] = Field(
        default_factory=list,
        description="Fully decomposed steps — only for rank 1. Leave empty for rank 2/3; they're decomposed later, only if needed.",
    )
    status: ApproachStatus = "pending"
    # Set by evaluate_approach on failure; fed into refine_approach for the
    # next rank so it can learn from what went wrong instead of repeating it.
    failure_reason: str | None = None


class Branch(BaseModel):
    branch_id: str = Field(description="Short identifier, e.g. b1, b2 — unique within this query's branches.")
    sub_query: str = Field(description="The independent sub-intent of the user's question this branch addresses.")
    approaches: list[Approach] = Field(description="Rank-ordered, 1-3 entries.")


class StepTable(BaseModel):
    """Generic tabular shape for a step's output — the stepper UI's Output
    section renders this as a table when present, instead of raw JSON."""

    columns: list[str]
    rows: list[list[Any]] = Field(default_factory=list)


class StepCalculation(BaseModel):
    """Explains a derived/aggregated value in the step's output — e.g. a sum,
    average, or discount applied — so the stepper UI can show the reasoning
    instead of just the final number."""

    formula: str  # e.g. "total = sum(quantity * unit_price) - discount"
    example: str | None = None  # e.g. "3 x $10.00 - $5.00 discount = $25.00"


class StepResult(BaseModel):
    step_id: str
    # Copied from the owning PlanStep so the frontend can group/order
    # step_results into per-branch steppers with approach markers without
    # cross-referencing state.branches.
    branch_id: str
    approach_rank: int
    source: Source
    # The specific API endpoint / SQL view-function / RAG document (+section,
    # once rag_node is implemented) this step used. Body content, not just a
    # trace detail — but only for State.view_mode == "stepper_debug" (manager
    # with debug=True); "stepper" (worker, or manager without debug) shows
    # `source` only, never this. See State.view_mode's docstring.
    resource: str
    # The step's planned intent (PlanStep.description), copied onto the
    # result so a stepper node can be rendered from step_results alone,
    # without cross-referencing the plan.
    description: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    # Human-readable account of what the node actually did — e.g. "fetched
    # 12 rows from customerdb.ss.get_orders". Distinct from `description`
    # (the planned intent): this is filled in once the worker node runs, and
    # is None until then (worker nodes are still stubs).
    operation_summary: str | None = None
    output: Any = None
    output_table: StepTable | None = None
    # Set only when the output involves a derived/computed value (a total,
    # an average, a discount, ...) worth explaining rather than just stating.
    calculation: StepCalculation | None = None
    error: str | None = None
