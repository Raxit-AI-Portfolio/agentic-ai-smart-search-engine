import html

import streamlit as st

from agentic_core.state.models.plan_models import Approach, Branch, StepResult

_SOURCE_LABEL = {"sql": "Database", "rag": "Document", "api": "API"}

# Scoped to div[data-testid="stExpander"] but explicitly excluding any
# expander nested inside stExpanderDetails (an expander's own body) — the
# collapsible "Trace" section is itself an st.expander() inside the step
# expander's body, and without the exclusion rule it would inherit the same
# connecting-line/dot styling meant only for the top-level step nodes.
# Verified against Streamlit 1.58's actual DOM (stExpanderDetails is the
# real testid for an expander's content wrapper).
#
# .efsse-approach-marker reuses the same connecting-line/dot look but is a
# plain div, not an st.expander — it must be non-expandable per the design
# (a fixed "a new approach started" marker, not a collapsible step).
_STEPPER_CSS = """
<style>
div[data-testid="stExpander"] {
    position: relative;
    margin-left: 14px;
    padding-left: 18px;
    border-left: 2px solid rgba(130, 130, 130, 0.35);
}
div[data-testid="stExpander"]::before {
    content: "";
    position: absolute;
    left: -7px;
    top: 18px;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: rgba(130, 130, 130, 0.9);
}
div[data-testid="stExpanderDetails"] div[data-testid="stExpander"] {
    border-left: none;
    margin-left: 0;
    padding-left: 0;
}
div[data-testid="stExpanderDetails"] div[data-testid="stExpander"]::before {
    display: none;
}
div.efsse-approach-marker {
    position: relative;
    margin-left: 14px;
    margin-bottom: 8px;
    padding: 6px 12px 6px 18px;
    border-left: 2px solid rgba(130, 130, 130, 0.35);
    background: rgba(130, 130, 130, 0.18);
    border-radius: 4px;
    font-size: 0.85rem;
}
div.efsse-approach-marker::before {
    content: "";
    position: absolute;
    left: -7px;
    top: 14px;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: rgba(130, 130, 130, 0.9);
}
</style>
"""


def _render_kv_table(data: dict) -> None:
    if not data:
        st.caption("(none)")
        return
    st.table({"Field": list(data.keys()), "Value": [str(v) for v in data.values()]})


def _render_operations(result: StepResult) -> None:
    # Never surface operation_summary as-is here — it embeds the resource
    # identifier (filename / endpoint / table); the role-agnostic planned
    # description is what's safe to show outside the debug Trace section.
    st.write(result.description)


def _render_output(result: StepResult) -> None:
    if result.error:
        st.error(result.error)
        return

    if result.output_table is not None:
        columns = result.output_table.columns
        rows = result.output_table.rows
        st.dataframe([dict(zip(columns, row)) for row in rows], use_container_width=True)
        return

    if result.source == "rag":
        st.write(f"Found {len(result.output or [])} relevant passage(s).")
        return

    if isinstance(result.output, list) and result.output and isinstance(result.output[0], dict):
        st.dataframe(result.output, use_container_width=True)
    elif isinstance(result.output, dict):
        _render_kv_table(result.output)
    elif result.output is not None:
        st.write(result.output)
    else:
        st.caption("(no output)")


def _render_trace(result: StepResult) -> None:
    """Manager+debug-only internals: the real resource identifier, the
    unredacted operation summary, and (for RAG) the actual retrieved
    passages — API endpoints / DB objects / document sections."""
    with st.expander("Trace", expanded=False):
        st.markdown(f"**Resource:** `{result.resource}`")
        if result.operation_summary:
            st.markdown(f"**Operation:** {result.operation_summary}")

        if result.source == "rag" and result.output:
            st.dataframe(
                [
                    {
                        "file": chunk.get("source_file"),
                        "section": chunk.get("header_path"),
                        "score": round(chunk.get("score", 0), 3),
                        "text": chunk.get("text"),
                    }
                    for chunk in result.output
                ],
                use_container_width=True,
            )


def _render_approach_marker(approach: Approach) -> None:
    """Non-expandable dark-gray node inserted whenever a branch's stepper
    moves onto a new approach — st.markdown, not st.expander, since it isn't
    a step to open/close, just a fixed timeline marker."""
    confidence_pct = round(approach.confidence * 100)
    strategy = html.escape(approach.strategy)
    st.markdown(
        f'<div class="efsse-approach-marker">Approach {approach.rank} '
        f"(confidence {confidence_pct}%): {strategy}</div>",
        unsafe_allow_html=True,
    )


def _result_identity(result: StepResult) -> tuple[str, int, str]:
    return (result.branch_id, result.approach_rank, result.step_id)


def _render_branch_outcome(branch: Branch) -> None:
    """A trailing marker for a branch that ended in failure — makes it
    explicit whether that was "gave up after trying every approach" or "only
    one approach was ever proposed", instead of the absence of a retry
    marker being the only (easy-to-miss) signal that nothing more was
    attempted."""
    attempted = sorted((a for a in branch.approaches if a.status != "pending"), key=lambda a: a.rank)
    if not attempted or attempted[-1].status != "failed":
        return
    last = attempted[-1]
    reason = html.escape(last.failure_reason or "no reason recorded")
    st.markdown(
        f'<div class="efsse-approach-marker">⚠️ Could not fully answer this part after '
        f"{len(attempted)} of {len(branch.approaches)} approach(es) — {reason}</div>",
        unsafe_allow_html=True,
    )


def _group_by_branch(step_results: dict[str, StepResult]) -> dict[str, list[StepResult]]:
    grouped: dict[str, list[StepResult]] = {}
    for result in step_results.values():
        grouped.setdefault(result.branch_id, []).append(result)
    return grouped


def render_stepper(step_results: dict[str, StepResult], branches: dict[str, Branch], *, show_resource: bool) -> None:
    """Renders one vertical stepper per branch (unrelated parts of a compound
    query run concurrently, so each gets its own timeline instead of being
    flattened into one sequential list) — within a branch, a dark-gray
    approach marker is inserted whenever its steps move onto a new approach,
    and failed approaches' step nodes stay visible above it for transparency.
    The single most-recently-arrived step (across all branches) is
    auto-expanded, matching the chat window's answer display."""
    if not step_results:
        st.caption("Waiting for the first step to complete...")
        return

    st.markdown(_STEPPER_CSS, unsafe_allow_html=True)

    by_branch = _group_by_branch(step_results)
    # branches (accumulated from planning_node's single all-at-once update)
    # preserves the plan's own branch ordering; fall back to arrival order
    # for any branch missing from it (shouldn't normally happen).
    branch_ids = [bid for bid in branches if bid in by_branch]
    branch_ids += [bid for bid in by_branch if bid not in branches]

    most_recent = _result_identity(list(step_results.values())[-1])

    for index, branch_id in enumerate(branch_ids):
        branch = branches.get(branch_id)
        results = by_branch[branch_id]

        if index > 0:
            st.divider()
        if branch is not None:
            st.markdown(f"#### {branch.sub_query}")

        current_rank: int | None = None
        for result in results:
            if result.approach_rank != current_rank:
                current_rank = result.approach_rank
                approach = next((a for a in branch.approaches if a.rank == current_rank), None) if branch else None
                if approach is not None:
                    _render_approach_marker(approach)

            source_label = _SOURCE_LABEL.get(result.source, result.source)
            status = "⚠️" if result.error else "✓"
            header = f"{status}  Data retrieved from {source_label} — {result.description}"
            expanded = bool(result.error) or _result_identity(result) == most_recent

            with st.expander(header, expanded=expanded):
                st.markdown("**Inputs**")
                _render_kv_table(result.inputs)

                st.markdown("**Operations**")
                _render_operations(result)

                if show_resource:
                    _render_trace(result)

                st.markdown("**Output**")
                _render_output(result)

        if branch is not None:
            _render_branch_outcome(branch)
