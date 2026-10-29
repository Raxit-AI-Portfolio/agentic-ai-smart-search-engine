import streamlit as st

_DEFAULTS = {
    "auth": None,  # frontend.auth_client.LoginResult | None
    "messages": [],  # [{"role": "user"|"assistant", "content": str}]
    "running": False,
    "last_step_results": {},  # step_id -> StepResult, for the stepper
    "last_branches": {},  # branch_id -> Branch, for the stepper's per-branch grouping + approach markers
    "debug_enabled": False,
}


def init_session() -> None:
    for key, default in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default


def clear_chat() -> None:
    st.session_state["messages"] = []
    st.session_state["last_step_results"] = {}
    st.session_state["last_branches"] = {}


def is_logged_in() -> bool:
    return st.session_state.get("auth") is not None
