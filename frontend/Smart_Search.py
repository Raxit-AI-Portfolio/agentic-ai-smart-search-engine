"""EFSSE Streamlit UI entrypoint — the Search page. Run with:
    streamlit run frontend/Smart_Search.py
No login screen: the demo scenario dropdown drives login/logout against the
real auth-api, exactly as a login page/logout button would.
"""

import sys
from pathlib import Path

# streamlit run puts this file's own directory (frontend/) on sys.path, not
# the repo root — so the root-level agentic_core package needs to be added
# explicitly before it can be imported.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import streamlit as st

from agentic_core.state.state import State
from frontend import auth_client
from frontend.components.stepper import render_stepper
from frontend.graph_runner import run_query
from frontend.scenarios import SCENARIOS
from frontend.session import clear_chat, init_session, is_logged_in

st.set_page_config(page_title="EFSSE — Smart Search", layout="wide")
init_session()

_DIVIDER_CSS = """
<style>
div[data-testid="stHorizontalBlock"] { align-items: stretch; }
div[data-testid="column"]:has(> div.efsse-divider) {
    display: flex;
    justify-content: center;
}
div.efsse-divider {
    width: 1px;
    height: 100%;
    min-height: 85vh;
    background: rgba(130, 130, 130, 0.35);
}
/* The composer's "Press Enter to submit form" hint renders on top of the
   text_input's own placeholder text since the input is collapsed-label and
   tightly spaced next to the Send button — hide it. */
div[data-testid="InputInstructions"] {
    display: none;
}
</style>
"""


def _switch_scenario(scenario_label: str) -> None:
    scenario = next(s for s in SCENARIOS if s.label == scenario_label)

    if is_logged_in():
        auth_client.logout(st.session_state["auth"].token)

    st.session_state["auth"] = auth_client.login(scenario.username, scenario.password)
    st.session_state["debug_enabled"] = scenario.debug
    clear_chat()
    st.session_state["last_view_mode"] = None
    st.session_state["running"] = False
    st.session_state["active_prompt"] = None
    # Drop any stale placeholder from a previous scenario's execution panel —
    # customer scenarios never recreate it (no right column), so leaving a
    # prior manager/worker run's st.empty() around lets a later _on_update
    # write into a DeltaGenerator whose layout no longer exists, which blanks
    # the whole page instead of raising a catchable exception.
    st.session_state.pop("_stepper_placeholder", None)
    # Pre-fill the composer rather than sending immediately — a demo
    # presenter reviews/edits the loaded scenario prompt and submits it
    # themselves (Enter or the Send button), same as a manually typed one.
    # Not written to the widget's own session_state key — see the composer
    # widget below for why.
    st.session_state["composer_prefill"] = scenario.prompt


def _execute(prompt: str) -> None:
    auth = st.session_state["auth"]
    # None for a customer — the execution panel (and its placeholder) is
    # never created for that role, since customers get answer-only output.
    stepper_placeholder = st.session_state.get("_stepper_placeholder")

    def _on_update(accumulated: dict) -> None:
        st.session_state["last_step_results"] = accumulated["step_results"]
        st.session_state["last_branches"] = accumulated["branches"]
        if stepper_placeholder is None:
            return
        state = State(**accumulated)
        with stepper_placeholder.container():
            if state.view_mode != "direct":
                render_stepper(
                    accumulated["step_results"],
                    accumulated["branches"],
                    show_resource=(state.view_mode == "stepper_debug"),
                )

    try:
        final = run_query(prompt, auth.token, st.session_state["debug_enabled"], _on_update)
        final_state = State(**final)
        st.session_state["messages"].append({"role": "assistant", "content": final_state.answer})
        st.session_state["last_step_results"] = final_state.step_results
        st.session_state["last_branches"] = final_state.branches
        st.session_state["last_view_mode"] = final_state.view_mode
    except Exception as exc:
        # Never leave `running` stuck on an unhandled failure (a transient
        # LLM/network error, say) — that previously wedged the composer
        # disabled with no way to recover short of reloading the page.
        st.session_state["messages"].append(
            {"role": "assistant", "content": f"Something went wrong processing that request: {exc}"}
        )
    finally:
        st.session_state["running"] = False
        st.session_state["active_prompt"] = None


st.title("Enterprise Federated Smart Search Engine")

role = st.session_state["auth"].role if is_logged_in() else None
show_execution_panel = role != "customer"

if show_execution_panel:
    left, divider, right = st.columns([1, 0.04, 1.3], gap="large")
    with divider:
        st.markdown(_DIVIDER_CSS + '<div class="efsse-divider"></div>', unsafe_allow_html=True)
else:
    (left,) = st.columns([1])

with left:
    st.subheader("Demo controls")
    labels = [s.label for s in SCENARIOS]
    current_label = st.session_state.get("scenario_label", labels[0])
    selected = st.selectbox("Load test scenario", labels, index=labels.index(current_label) if current_label in labels else 0)
    if selected != st.session_state.get("scenario_label"):
        st.session_state["scenario_label"] = selected
        _switch_scenario(selected)
        st.rerun()

    if is_logged_in():
        auth = st.session_state["auth"]
        st.caption(f"Logged in as **{auth.username}** ({auth.role})")
    else:
        st.info("Select a scenario above to log in and begin.")

    st.divider()
    st.subheader("Chat")

    # A stable key tied to the logged-in identity forces Streamlit to remount
    # this scrollable container on scenario switch instead of diffing the
    # old one — otherwise its previous children can visibly linger for a
    # render or two after messages has already been cleared.
    chat_key = f"chat_{st.session_state['auth'].token[:8]}" if is_logged_in() else "chat_anon"
    chat_container = st.container(height=420, key=chat_key)
    with chat_container:
        for message in st.session_state["messages"]:
            with st.chat_message(message["role"]):
                st.write(message["content"])

    disabled = not is_logged_in() or st.session_state["running"]

    if is_logged_in() and st.session_state["auth"].role == "manager":
        st.session_state["debug_enabled"] = st.toggle("Debug", value=st.session_state["debug_enabled"])

    # A plain st.chat_input can't be pre-filled programmatically, which the
    # "load scenario into the box, presenter reviews then sends" workflow
    # needs — so the composer is a form instead: enter_to_submit=True keeps
    # the same "Enter or click Send" behavior, and clear_on_submit resets it
    # for the next message.
    #
    # The widget's `key` changes per scenario (not a fixed key we mutate via
    # session_state) so each scenario switch mounts a genuinely new widget
    # seeded from `value=` — Streamlit only honors `value=` on a key's first
    # mount, so writing directly to a stable key's session_state entry from
    # outside (the previous approach) was unreliable: whether it "took"
    # depended on exactly when Streamlit considered that key already live.
    composer_key = f"composer_{st.session_state.get('scenario_label', '')}"
    with st.form("composer", clear_on_submit=True, border=False):
        composer_cols = st.columns([5, 1])
        with composer_cols[0]:
            typed = st.text_input(
                "Message",
                value=st.session_state.get("composer_prefill", ""),
                key=composer_key,
                placeholder="Ask a question...",
                disabled=disabled,
                label_visibility="collapsed",
            )
        with composer_cols[1]:
            submitted = st.form_submit_button("Send", disabled=disabled, use_container_width=True)

    if st.session_state["running"]:
        st.info("Processing your request...")

if show_execution_panel:
    with right:
        has_started = st.session_state["running"] or st.session_state.get("last_view_mode") is not None
        if has_started:
            st.subheader("Search Request Execution")
        st.session_state["_stepper_placeholder"] = st.empty()

        # Repaint from the last completed run's state on every rerun (e.g.
        # after this script's own closing st.rerun() calls) — the live
        # _on_update callback only writes here while a run is in flight.
        if is_logged_in() and not st.session_state["running"]:
            view_mode = st.session_state.get("last_view_mode")
            if view_mode and view_mode != "direct":
                with st.session_state["_stepper_placeholder"].container():
                    render_stepper(
                        st.session_state["last_step_results"],
                        st.session_state["last_branches"],
                        show_resource=(view_mode == "stepper_debug"),
                    )

# --- Phase 1: the composer was submitted (Enter or Send) while idle — show
# the message in chat immediately and flip to "running" before doing any
# actual (slow) work, so the UI never sits on stale content mid-run. ---
if not st.session_state["running"] and submitted and typed and is_logged_in():
    st.session_state["messages"].append({"role": "user", "content": typed})
    st.session_state["last_step_results"] = {}
    st.session_state["last_branches"] = {}
    st.session_state["active_prompt"] = typed
    st.session_state["running"] = True
    st.rerun()

# --- Phase 2: actually run the graph for the prompt queued in phase 1. ---
if st.session_state["running"] and st.session_state.get("active_prompt"):
    _execute(st.session_state["active_prompt"])
    st.rerun()
