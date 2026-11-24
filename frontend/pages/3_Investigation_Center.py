"""Investigation Center: select an incident, run the six-agent investigation, review
progress, findings, evidence and resolve human approvals.

Data: GET /incidents, GET /incidents/{id}, GET /incidents/{id}/investigations,
POST /investigations/{incident_id}/run, POST /approvals/{investigation_id}.
"""
import streamlit as st

from sentinelx_ui import api, charts
from sentinelx_ui.components import esc
from sentinelx_ui.navigation import header, page_setup, rerun_app, show_api_error
from sentinelx_ui.views import investigation as V
from sentinelx_ui.widgets import (empty_state, fmt_ts, notice, progress, section_title, severity_badge, status_badge)

page_setup("Investigation Center", "🧭")
header("Investigation Center", "Run, monitor and review multi-agent incident investigations.",
       eyebrow="OPERATIONS / INVESTIGATION CENTER")

inc_res = api.incident_list()
if not inc_res.ok:
    show_api_error(inc_res, "incidents")
incidents = [i for i in (inc_res.data or []) if i.get("id")]
if not incidents:
    st.markdown(empty_state("No incidents yet", "Upload security logs in the Log Explorer to create an incident."), unsafe_allow_html=True)
    st.page_link("pages/2_Log_Explorer.py", label="Open Log Explorer", icon=":material/manage_search:")
    st.stop()

labels = {i["id"]: f'{(i.get("severity") or "unscored").capitalize()} · {i.get("title") or "Untitled"} · {i["id"][:8]}' for i in incidents}
goto = st.session_state.pop("selected_incident_id", None)
if goto in labels:
    st.session_state["ic_pick"] = goto
if st.session_state.get("ic_pick") not in labels:
    st.session_state["ic_pick"] = incidents[0]["id"]

top = st.columns([4, 1.3, 1])
incident_id = top[0].selectbox("Incident", list(labels), key="ic_pick", format_func=lambda i: labels[i],
                               label_visibility="collapsed")
refresh = top[2].button("↻ Refresh", key="ic_refresh", use_container_width=True)
if refresh:
    api.invalidate()


def load(force: bool = False):
    d = api.fetch(f"/incidents/{incident_id}", ttl=4, force=force)
    v = api.fetch(f"/incidents/{incident_id}/investigations", ttl=4, force=force)
    return d, v


details, invs = load()
if not details.ok:
    show_api_error(details, "the incident")
if not invs.ok:
    show_api_error(invs, "the investigation history")

investigations = invs.data["investigations"]
latest_status = (investigations[0]["status"] if investigations else "") or ""
running = latest_status.lower() == "running"

if top[1].button("Re-run investigation" if investigations else "Run investigation", key="ic_run", type="primary",
                 use_container_width=True, disabled=running, icon=":material/play_arrow:"):
    with st.spinner("Starting the investigation workflow…"):
        run = api.post(f"/investigations/{incident_id}/run")
    if run.ok:
        api.invalidate()
        rerun_app()
    else:
        st.error(f"Investigation could not be started: {run.error or 'backend unreachable'}")


def render() -> None:
    d, v = load(force=False)
    if not (d.ok and v.ok):
        show_api_error(d if not d.ok else v, "the investigation", stop=False)
        return
    incident, events = d.data, d.data.get("events") or []
    runs = v.data["investigations"]

    inv = None
    if runs:
        idx = 0
        if len(runs) > 1:
            names = [f'{fmt_ts(r["created_at"])} · {r["status"]}' for r in runs]
            idx = names.index(st.selectbox("Investigation run", names, key="ic_run_pick"))
        inv = runs[idx]
    pending = [a for a in (inv or {}).get("approvals", []) if a.get("status") == "pending"]

    st.markdown(V.kpis(incident, inv, incident.get("events_count"), len(runs), len(pending)), unsafe_allow_html=True)
    if incident.get("description"):
        st.markdown(f'<div class="sx-muted" style="margin:-4px 0 10px">{esc(incident["description"])}</div>', unsafe_allow_html=True)

    left, right = st.columns([2.2, 1])
    with left, st.container(key="sxp_ic_progress"):
        st.markdown(section_title("Investigation progress", "Agent states come from recorded agent runs only.",
                                  right_html=status_badge((inv or {}).get("status") or "pending") if inv else ""), unsafe_allow_html=True)
        if not inv:
            st.markdown(notice("No investigation has been run for this incident yet. Use “Run investigation” above.", "info"), unsafe_allow_html=True)
        status = ((inv or {}).get("status") or "").lower()
        note = {"running": "Investigation running. Agent results are recorded when the pipeline finishes; this view refreshes automatically.",
                "failed": "The investigation failed. Use “Re-run investigation” to retry.",
                "awaiting_review": "The pipeline stopped for human review; no automated response was recorded."}.get(status, "")
        st.markdown(charts.pipeline_svg(V.agent_states(inv), note), unsafe_allow_html=True)
        pct = V.progress_pct(inv)
        st.markdown(progress(pct, "ok" if pct == 100 else ("critical" if status == "failed" else "blue"),
                             f"{pct:.0f}% of agents have recorded results"), unsafe_allow_html=True)
        if inv and inv.get("summary"):
            st.markdown(f'<div class="sx-sub">Investigation summary</div><div class="sx-findings">{esc(inv["summary"])}</div>',
                        unsafe_allow_html=True)
    with left, st.container(key="sxp_ic_overview"):
        st.markdown(section_title("Incident overview", "Recorded incident facts and the evidence it contains."), unsafe_allow_html=True)
        st.markdown(V.overview(incident, events), unsafe_allow_html=True)
    with right, st.container(key="sxp_ic_timeline"):
        st.markdown(section_title("Investigation timeline", "Chronological activity from recorded timestamps."), unsafe_allow_html=True)
        st.markdown(V.timeline(incident, inv), unsafe_allow_html=True)

    t1, t2, t3, t4 = st.tabs(["Findings & recommendations", "Evidence", "Agent results", f"Approvals ({len(pending)} pending)"])
    with t1, st.container(key="sxp_ic_findings"):
        st.markdown(V.findings(inv), unsafe_allow_html=True)
    with t2:
        ev = V.evidence(events)
        c1, c2 = st.columns([1, 2.2])
        with c1, st.container(key="sxp_ic_evtypes"):
            st.markdown(section_title("Events by type"), unsafe_allow_html=True)
            st.markdown(ev["chart"], unsafe_allow_html=True)
        with c2:
            st.markdown(ev["table"], unsafe_allow_html=True)
    with t3:
        st.markdown(V.agent_results(inv), unsafe_allow_html=True)
    with t4:
        approvals = (inv or {}).get("approvals", [])
        if not approvals:
            st.markdown(empty_state("No approval requested", "Approvals are created when the Response Agent proposes actions that need a human decision."),
                        unsafe_allow_html=True)
        for a in approvals:
            st.markdown(V.approval_card(a), unsafe_allow_html=True)
            if a.get("status") == "pending":
                b1, b2, _ = st.columns([1, 1, 4])
                for col, action, label, kind in ((b1, "approve", "Approve", "primary"), (b2, "reject", "Reject", "secondary")):
                    if col.button(label, key=f'ic_{action}_{a["id"]}', type=kind, use_container_width=True):
                        res = api.post(f'/approvals/{inv["id"]}', {"action": action})
                        if res.ok:
                            api.invalidate()
                            rerun_app()
                        else:
                            st.error(f"Could not record the decision: {res.error or 'backend unreachable'}")


if running:
    st.fragment(render, run_every=5)()
else:
    render()
