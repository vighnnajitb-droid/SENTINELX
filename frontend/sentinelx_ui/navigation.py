"""Global navigation shared by every page.

Each page starts with ``page_setup(...)``. It performs, in order:
  1. st.set_page_config (must be the first Streamlit call)
  2. the shared theme
  3. the authentication gate (no token => message + link to login, then stop)
  4. the unified sidebar (branding, navigation with active highlight, account, logout)
"""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from . import api
from .components import esc
from .theme import apply_theme
from .widgets import page_header

NAV_GROUPS = [
    ("OPERATIONS", [
        ("pages/1_Command_Center.py", "Command Center", ":material/dashboard:"),
        ("pages/2_Log_Explorer.py", "Log Explorer", ":material/manage_search:"),
        ("pages/3_Investigation_Center.py", "Investigation Center", ":material/troubleshoot:"),
        ("pages/4_Agent_Operations.py", "Agent Operations", ":material/smart_toy:"),
    ]),
    ("INTELLIGENCE", [
        ("pages/5_Risk_Assessment.py", "Risk Assessment", ":material/query_stats:"),
        ("pages/6_Audit_Trail.py", "Audit Trail", ":material/fact_check:"),
        ("pages/7_Reports.py", "Reports", ":material/description:"),
    ]),
    ("PLATFORM", [
        ("pages/8_Settings.py", "Settings", ":material/settings:"),
    ]),
]


def _logout() -> None:
    api.end_session()
    st.session_state.pop("username", None)
    st.switch_page("app.py")


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            '<div class="sx-sb-brand"><div class="sx-sb-logo">S</div><div class="sx-sb-name">'
            '<b>SENTINEL<span>X</span></b><small>INCIDENT RESPONSE NETWORK</small></div></div>',
            unsafe_allow_html=True)
        for group, items in NAV_GROUPS:
            st.markdown(f'<div class="sx-sb-label">{group}</div>', unsafe_allow_html=True)
            for path, label, icon in items:
                st.page_link(path, label=label, icon=icon)

        name = api.username()
        expiry = api.session_expiry()
        session_line = "session active"
        if expiry:
            until = datetime.fromtimestamp(expiry, tz=timezone.utc)
            session_line = f"session until {until:%H:%M} UTC"
        st.markdown(
            f'<div class="sx-acct"><div class="sx-av">{esc(name[:1].upper() or "?")}</div>'
            f'<div><b title="{esc(name)}">{esc(name)}</b>'
            f'<small><span class="sx-live"></span>{esc(session_line)}</small></div></div>',
            unsafe_allow_html=True)
        if st.button("Log out", key="sx_logout", use_container_width=True, icon=":material/logout:"):
            _logout()


def page_setup(title: str, icon: str, dashboard: bool = False) -> None:
    st.set_page_config(page_title=f"SENTINELX | {title}", page_icon=icon, layout="wide",
                       initial_sidebar_state="expanded")
    apply_theme(dashboard=dashboard)
    if not st.session_state.get("token"):
        st.markdown(page_header("Authentication required", "Sign in to open this workspace."), unsafe_allow_html=True)
        st.page_link("app.py", label="Go to sign in", icon=":material/login:")
        st.stop()
    render_sidebar()


def header(title: str, subtitle: str = "", eyebrow: str = "", right_html: str = "") -> None:
    st.markdown(page_header(title, subtitle, eyebrow, right_html), unsafe_allow_html=True)


def show_api_error(result: "api.ApiResult", what: str, stop: bool = True) -> None:
    """Render a consistent error state for a failed API call, optionally stopping the page."""
    from .widgets import error_state, notice
    if result.unauthorized:
        st.markdown(error_state("Session expired", "Your session is no longer valid. Sign in again to continue."),
                    unsafe_allow_html=True)
        st.page_link("app.py", label="Go to sign in", icon=":material/login:")
    elif not result.reachable:
        st.markdown(error_state("Backend unreachable", f"Could not load {what}. Check that the API is running at {api.API_URL}."),
                    unsafe_allow_html=True)
    elif result.status == 404:
        st.markdown(notice(f"{what} is not available on this backend version. Update the backend to enable it.", "warn"),
                    unsafe_allow_html=True)
    else:
        st.markdown(error_state(f"Could not load {what}", f"HTTP {result.status}: {result.error or 'unexpected response'}"),
                    unsafe_allow_html=True)
    if stop:
        st.stop()


def rerun_app() -> None:
    """Full-app rerun that also works when called from inside an st.fragment."""
    try:
        st.rerun(scope="app")
    except TypeError:
        st.rerun()
