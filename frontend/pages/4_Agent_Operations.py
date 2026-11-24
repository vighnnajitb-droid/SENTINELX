"""Agent Operations: multi-agent console built from recorded agent runs.

Data: GET /agents/overview, POST /investigations/{incident_id}/run (retry).
No execution result is invented: agents that never ran show 'Not run yet'.
"""
import streamlit as st

from sentinelx_ui import api, charts
from sentinelx_ui.components import esc
from sentinelx_ui.navigation import header, page_setup, rerun_app, show_api_error
from sentinelx_ui.views import agents as V
from sentinelx_ui.widgets import empty_state, notice, section_title

page_setup("Agent Operations", "🤖")
header("Agent Operations", "Status, execution history and orchestration of the six SENTINELX agents.",
       eyebrow="OPERATIONS / AGENT OPERATIONS")

bar = st.columns([1.3, 1.3, 1.1, 1])
if bar[3].button("↻ Refresh", key="ao_refresh", use_container_width=True):
    api.invalidate()

res = api.fetch("/agents/overview", ttl=10)
if not res.ok:
    show_api_error(res, "agent operations")
ov = res.data

st.markdown(V.kpis(ov), unsafe_allow_html=True)

with st.container(key="sxp_ao_flow"):
    st.markdown(section_title("Agent workflow", "Colour shows each agent's most recent recorded run status. "
                              "Flow order follows the LangGraph pipeline: detect, investigate, enrich, assess, audit, respond."),
                unsafe_allow_html=True)
    st.markdown(charts.pipeline_svg(V.flow_states(ov["agents"]),
                                    "Detection → Investigation → Threat Intel → Risk → Audit → Response. "
                                    "Response is withheld when the audit step does not verify evidence."), unsafe_allow_html=True)

st.markdown(V.agent_cards(ov["agents"]), unsafe_allow_html=True)

st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
left, right = st.columns([1.7, 1])
with left:
    agent_names = [a["name"] for a in ov["agents"]]
    f1, f2, _ = st.columns([1.4, 1.2, 2])
    agent_f = f1.selectbox("Agent", ["All agents"] + agent_names, key="ao_agent", label_visibility="collapsed",
                           format_func=lambda n: n if n == "All agents" else V.LABEL.get(n, n) + " Agent")
    status_f = f2.selectbox("Status", ["All statuses", "completed", "failed"], key="ao_status", label_visibility="collapsed")
    runs = [r for r in ov["runs"] if (agent_f == "All agents" or r["agent_name"] == agent_f)
            and (status_f == "All statuses" or (r.get("status") or "").lower() == status_f)]
    st.markdown(section_title("Execution history", right_html=f'<span class="sx-muted">{len(runs)} of {len(ov["runs"])} recent runs</span>'),
                unsafe_allow_html=True)
    st.markdown(V.run_history(runs), unsafe_allow_html=True)
with right:
    st.markdown(section_title("Orchestration activity", "Most recent investigations and their pipeline status."), unsafe_allow_html=True)
    st.markdown(V.orchestration(ov["investigations"]["recent"]), unsafe_allow_html=True)

failed = [i for i in ov["investigations"]["recent"] if i.get("status") == "failed"]
st.markdown(section_title("Error and retry"), unsafe_allow_html=True)
if not failed:
    st.markdown(notice("No failed investigations among the most recent runs.", "ok"), unsafe_allow_html=True)
for inv in failed[:5]:
    c1, c2 = st.columns([4, 1])
    c1.markdown(f'<div class="sx-notice error">Investigation for <b>{esc(inv.get("incident_title") or inv["incident_id"])}</b> failed.</div>',
                unsafe_allow_html=True)
    if c2.button("Retry", key=f'ao_retry_{inv["id"]}', use_container_width=True, icon=":material/replay:"):
        run = api.post(f'/investigations/{inv["incident_id"]}/run')
        if run.ok:
            api.invalidate()
            rerun_app()
        else:
            st.error(f"Retry could not be started: {run.error or 'backend unreachable'}")
