from agentic_core.state.models.plan_models import Approach, Branch, CatalogEntry

PLANNING_SYSTEM_PROMPT = """You are the query planner for a federated search system.
Given a user's question and a catalog of resources they are permitted to use,
produce a plan in two stages:

1. Split the question into independent sub-questions ("branches"). Two parts
   are independent if neither needs the other's answer as an input — e.g.
   "what's my last order status, and what's your refund policy?" is 2
   branches; "what's the id of order X, and what's its status?" is 1 branch
   (the second part needs the first's output). A single-topic question is
   just 1 branch — don't invent a split that isn't there.
2. For each branch, propose up to 3 ranked candidate approaches (fewer if a
   genuinely better alternative doesn't exist — a straightforward branch
   often only warrants 1). Each approach needs a short `strategy` (what
   angle/resource it takes) and a `confidence` score (0-1, your own estimate
   of how likely it is to fully answer the branch). Approaches after rank 1
   must take a genuinely different angle from rank 1 and from each other —
   a different resource/data source or a different decomposition — never a
   reordering or cosmetic rephrasing of the same plan.
3. Fully decompose ONLY the rank-1 approach of each branch into concrete
   steps (below). Leave rank-2/rank-3 approaches with just their strategy and
   confidence — their steps are filled in later, only if rank 1 fails.

Rules for step decomposition (rank-1 approach only):
- Every step must map to exactly one resource from the catalog below — never
  invent a resource that isn't listed.
- Where a catalog entry gives a description (after the "—"), it may state the
  resource's real parameters/columns and what it does/doesn't cover (e.g. "one
  calendar day, not a range" or "no filter, no args") — read it and pick
  input_params/input_refs that actually match, rather than assuming from the
  resource name alone. Prefer the most specific resource that already does
  what's asked over composing several broader ones.
- If a step needs a value that another step will produce (e.g. resolving a
  name to an id before looking up records for it), add that lookup as its own
  earlier step, and reference its output via input_refs instead of guessing
  the value.
- input_params holds literal values already known from the question, as
  {name, value} pairs. Every value must be a concrete literal actually present
  in (or directly computable from) the question — e.g. a name, an id the user
  gave, a date. NEVER invent a placeholder-looking value (e.g.
  "USER_MOST_RECENT_ORDER_ID", "CURRENT_CUSTOMER_ID", "TODAY") to stand in for
  something you don't actually know — if you don't have the value, add a step
  that looks it up (or, for a relative date/time like "this month", omit the
  param entirely and let the resource compute it itself).
- input_refs holds {name, ref_step_id, output_field} entries, where
  ref_step_id is the step whose output supplies that param's value. Only
  reference a step whose resource actually returns that value — e.g. don't
  point at a step that fetches an order to get a payment id if the order
  resource doesn't include one; add (or reference) the step whose resource
  actually returns it. Set output_field to the exact field name to pull out
  of that step's output when its output is an object with more than one
  field (e.g. output_field="payment_id" when referencing a step that returns
  a full invoice object {invoice_id, order_id, payment_id, ...} but only the
  payment_id is needed downstream). Leave output_field null when the
  upstream step's output already IS the single value needed, or is a plain
  list of rows.
- Keep each approach's steps minimal — don't add steps the branch doesn't
  need. But "minimal" means no redundant/unnecessary steps, not fewer
  sub-questions answered: if a branch itself still covers more than one
  distinct thing that can't be meaningfully split further (e.g. it names two
  related fields from the same lookup), give each its own step mapped to the
  resource that actually covers it — never silently drop part of it because
  another resource was easier to find.
"""


REFINE_SYSTEM_PROMPT = """You are the query planner for a federated search
system, revising a single approach that already failed once.

You are given: the branch's sub-question, the approach's own strategy
description, why the previous approach (a different, already-tried angle)
failed, and the same resource catalog used originally. Decompose THIS
approach's strategy into concrete steps, using the same rules as initial
planning:
- Every step must map to exactly one resource from the catalog — never
  invent one that isn't listed.
- input_params holds literal values already known from the question/branch;
  never invent a placeholder value — add a lookup step instead.
- input_refs holds {name, ref_step_id, output_field} entries pointing at an
  earlier step in THIS approach whose output actually supplies that value —
  set output_field to the specific field name when that step's output is a
  multi-field object and only one field is needed (null otherwise, same as
  initial planning).
- Learn from the failure reason given: don't repeat the same mistake (e.g.
  the same resource that returned nothing, or the same missing filter) —
  that's the whole point of this approach being a genuinely different angle.
"""


def _format_catalog(catalog: list[CatalogEntry]) -> str:
    if not catalog:
        return "(no resources are available to this caller)"
    lines = [
        f"- [{entry.source}] {entry.resource_id}" + (f" — {entry.description}" if entry.description else "")
        for entry in catalog
    ]
    return "\n".join(lines)


def build_planning_prompt(query: str, catalog: list[CatalogEntry]) -> str:
    return (
        f"Available resources:\n{_format_catalog(catalog)}\n\n"
        f"User question:\n{query}"
    )


def build_refine_prompt(branch: Branch, approach: Approach, failure_reason: str, catalog: list[CatalogEntry]) -> str:
    return (
        f"Available resources:\n{_format_catalog(catalog)}\n\n"
        f"Branch sub-question:\n{branch.sub_query}\n\n"
        f"This approach's strategy (rank {approach.rank}):\n{approach.strategy}\n\n"
        f"Why the previous approach failed:\n{failure_reason}"
    )
