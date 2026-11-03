from agentic_core.state.models.plan_models import Branch, StepResult

SYNTHESIS_SYSTEM_PROMPT = """You are the synthesis step of a federated search system.
You are given the user's original question, broken into sub-questions, and
the results of every plan step that was run to answer each one (from SQL,
RAG, and/or API sources).

Rules:
- Address the sub-questions in the exact order they're given below — that
  order matches how the user originally asked them, so don't reorder,
  regroup, or lead with a later part just because its data looks richer.
- Answer using only the data in the step results below — never invent facts.
- Use whatever usable data exists for a sub-question, even if that
  sub-question also has an error/insufficient step alongside it — don't
  claim "no information" for a part that actually has real data just because
  one of its steps failed; cover what the data does show, then note what's
  missing using the ERROR-handling rules below.
- Never mention internal implementation details in the answer: no SQL
  function/view names, no database names, no API routes or HTTP methods, no
  step ids, and no RAG document filenames or section numbers either. Those
  are shown separately to the caller when appropriate (e.g. a manager's debug
  view) — your answer must read as plain business language, as if a person
  looked this up and explained it in their own words, not as if reading from
  a specific file. This applies even when a retrieved RAG passage's own text
  contains a filename, markdown link, or cross-reference (e.g. "see
  [order_processing_sop.md](order_processing_sop.md)") — paraphrase what it
  says instead of repeating the filename/link verbatim.
- If a step's result says "FAILED (details withheld)", tell the user that
  part of their request couldn't be completed and they should contact Smart
  Search Admin for help — do not guess at, restate, or speculate about what
  went wrong, since you were not given the technical detail. Do not mention
  which internal step or system failed.
- If a step's result gives a real ERROR message instead, explain in plain
  language what happened using that detail, still without naming internal
  resources/routes/functions.
- Write one concise, natural-language answer — no headers, no raw JSON.
"""


def _format_step(result: StepResult, debug: bool) -> str:
    if result.error:
        detail = result.error if debug else "FAILED (details withheld)"
        return f"- step {result.step_id} [{result.source}] {result.resource}: ERROR — {detail}"
    return f"- step {result.step_id} [{result.source}] {result.resource}: {result.output!r}"


def build_synthesis_prompt(
    query: str, branches: list[Branch], results_by_branch: dict[str, list[StepResult]], debug: bool
) -> str:
    sections = []
    for index, branch in enumerate(branches, start=1):
        results = results_by_branch.get(branch.branch_id, [])
        results_desc = "\n".join(_format_step(result, debug) for result in results) or "(no usable data for this part)"
        sections.append(f"{index}. Sub-question: {branch.sub_query}\n   Step results:\n{results_desc}")

    body = "\n\n".join(sections) or "(no steps were run)"
    return f"User question:\n{query}\n\nAnswer these sub-questions, in this order:\n\n{body}"
