import operator
from typing import Annotated, Literal

from pydantic import BaseModel, Field, computed_field

from agentic_core.state.models.plan_models import Branch, CatalogEntry, StepResult

Role = Literal["customer", "worker", "manager"]
ViewMode = Literal["direct", "stepper", "stepper_debug"]


class State(BaseModel):
    query: str
    # role must be derived from authorization_header (see
    # agentic_core/services/auth_service.py's build_initial_state), not set
    # independently — otherwise nothing guarantees the two agree.
    role: Role
    # The caller's JWT, forwarded as-is to the API MCP server so customer-api/
    # operations-api enforce access themselves rather than the graph re-authenticating.
    authorization_header: str
    # Manager-only request-time toggle for the extra debug detail in
    # view_mode below. Meaningless for customer/worker — view_mode ignores it
    # for those roles rather than trusting the caller to only set it when
    # they're actually a manager.
    debug: bool = False

    # Set by guardrail_node; False means execution stopped there and `answer`
    # already holds the rejection message — routes.guardrail_routing reads
    # this to skip straight to END instead of running intent/planning/fanout.
    guardrail_passed: bool = False

    # Resources the caller's role may use, across all 3 sources — built by
    # intent_node and the only thing planning_node is allowed to route to.
    catalog: list[CatalogEntry] = Field(default_factory=list)

    # One entry per independent sub-intent the query splits into (see
    # planning_service.decompose_query), keyed by branch_id. Like
    # step_results, this needs a merge-by-key reducer rather than
    # list-concat: a branch's own retry-loop subgraph (branch_node) writes
    # its entry more than once (status/steps change across execute/
    # evaluate/refine), and operator.or_'s dict union makes each write
    # cleanly replace the same key instead of accumulating stale duplicates.
    branches: Annotated[dict[str, Branch], operator.or_] = Field(default_factory=dict)
    # Transient — only meaningful inside the isolated state copy
    # orchestrator_node hands to one branch's retry-loop subgraph
    # (branch_node.branch_graph); identifies which Branch/Approach that
    # subgraph is currently acting on.
    active_branch_id: str = ""
    attempt_index: int = 0

    # Populated one entry per plan step as the step-graph executes, keyed by
    # a "branch_id.approach_rank.step_id" composite (see
    # execution_service._key) rather than bare step_id — branches run
    # concurrently and a retried approach can reuse the same step_ids, so a
    # bare step_id key would let a later attempt silently clobber an earlier
    # failed attempt's (still-wanted, for the stepper) results. Steps in the
    # same dependency batch run concurrently, so this needs a merge reducer
    # instead of last-write-wins — composite keys are what keep the union
    # collision-free.
    step_results: Annotated[dict[str, StepResult], operator.or_] = Field(default_factory=dict)

    # Nodes from the parallel fan-out append concurrently, so this needs a
    # reducer instead of last-write-wins.
    trace: Annotated[list[str], operator.add] = Field(default_factory=list)
    answer: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def view_mode(self) -> ViewMode:
        """How the UI should render the response — the single source of
        truth for the customer/worker/manager output rule, so app.py doesn't
        re-derive it (and risk getting the manager-only debug gating wrong).

        - customer: the synthesized answer only, no per-step stepper.
        - worker: the vertical stepper (state.step_results), without the
          specific resource identifiers (StepResult.resource) in each step's
          body — only the source category (sql/rag/api).
        - manager with debug=True: the stepper, with StepResult.resource
          (the API endpoint / DB object / document+section actually used)
          included in each step's body.
        """
        if self.role == "customer":
            return "direct"
        if self.role == "manager" and self.debug:
            return "stepper_debug"
        return "stepper"
