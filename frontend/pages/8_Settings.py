"""Settings: platform configuration status. Secret values are never shown.

Data: GET /system/info and GET /health from the backend, plus client-side
connection measurements. Sections mirror a settings-centre layout.
"""
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from sentinelx_ui import api
from sentinelx_ui.navigation import header, page_setup, show_api_error
from sentinelx_ui.views import settings as V
from sentinelx_ui.widgets import section_title

page_setup("Settings", "⚙️")
header("Platform Settings", "Connection status, authentication posture and safe configuration guidance.",
       eyebrow="PLATFORM / SETTINGS")

force = False
nav, body = st.columns([1, 3.2])
with nav, st.container(key="sxp_st_nav"):
    st.markdown(section_title("Sections"), unsafe_allow_html=True)
    section = st.radio("Section", V.SECTIONS, key="st_section", label_visibility="collapsed")
    if st.button("Run connection test", key="st_test", use_container_width=True, type="primary", icon=":material/network_check:"):
        force = True

info = api.fetch("/system/info", ttl=30, force=force)
health = api.fetch("/health", ttl=30, force=force)

with body, st.container(key="sxp_st_body"):
    st.markdown(section_title(section), unsafe_allow_html=True)
    if section == "Safe configuration":
        st.markdown(V.guidance(), unsafe_allow_html=True)
    elif not info.reachable:
        st.markdown(V.connection(api.API_URL, None, None, None, False), unsafe_allow_html=True)
        show_api_error(info, "system information", stop=False)
    elif not info.ok:
        show_api_error(info, "system information", stop=False)
    elif section == "Connection":
        st.markdown(V.connection(api.API_URL, health.data if health.ok else None, info.data, info.latency_ms, True), unsafe_allow_html=True)
    elif section == "Authentication":
        exp = api.session_expiry()
        when = datetime.fromtimestamp(exp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if exp else None
        st.markdown(V.authentication(info.data, api.username(), when), unsafe_allow_html=True)
    elif section == "Integrations":
        wf_dir = Path(__file__).resolve().parents[2] / "n8n-workflows"
        files = sorted(p.name for p in wf_dir.glob("*.json")) if wf_dir.exists() else []
        st.markdown(V.integrations(info.data, files), unsafe_allow_html=True)
    elif section == "Agents & LLM":
        st.markdown(V.agents_llm(info.data), unsafe_allow_html=True)
    elif section == "System":
        st.markdown(V.system(info.data, st.__version__), unsafe_allow_html=True)
