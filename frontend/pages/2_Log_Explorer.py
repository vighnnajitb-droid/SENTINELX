"""Log Explorer: search and inspect ingested events, and ingest new logs.

Data: GET /api/v1/events (search, filters, stats), POST /api/v1/logs/upload,
POST /api/v1/investigations/{incident_id}/run. Nothing is fabricated: empty
results render an empty state, failures render an error state.
"""
import math
from datetime import datetime, time
from pathlib import Path

import streamlit as st

from sentinelx_ui import api
from sentinelx_ui.navigation import header, page_setup, show_api_error
from sentinelx_ui.views import logs as V
from sentinelx_ui.widgets import (empty_state, notice, pager_text, section_title)

page_setup("Log Explorer", "🔍")
header("Log Explorer", "Search, filter and inspect security events, or ingest new logs for analysis.",
       eyebrow="OPERATIONS / LOG EXPLORER")

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "sample_data"
SEVERITIES = ["critical", "high", "medium", "low", "unscored"]
PAGE_SIZES = [25, 50, 100]

tab_search, tab_ingest = st.tabs(["Event search", "Ingest logs"])

# =============================================================== SEARCH
with tab_search:
    opts = api.fetch("/events", {"page_size": 1}, ttl=60)
    if not opts.ok:
        show_api_error(opts, "the event index")
    type_options = sorted((opts.data.get("stats", {}).get("by_type") or {}).keys())

    with st.form("lx_form", border=True):
        r1 = st.columns([3.2, 2.2, 2.2])
        q = r1[0].text_input("Search", key="lx_q", placeholder="IP address, event type, user, any field in the raw event…")
        types = r1[1].multiselect("Event category", type_options, key="lx_types", placeholder="All categories")
        sevs = r1[2].multiselect("Incident severity", SEVERITIES, key="lx_sevs", placeholder="All severities")
        r2 = st.columns([1.6, 1.6, 1.3, 1.3, 1.2])
        d_from = r2[0].date_input("From date", value=None, key="lx_from", format="YYYY-MM-DD")
        d_to = r2[1].date_input("To date", value=None, key="lx_to", format="YYYY-MM-DD")
        order = r2[2].selectbox("Sort", ["desc", "asc"], key="lx_order",
                                format_func=lambda o: "Newest first" if o == "desc" else "Oldest first")
        page_size = r2[3].selectbox("Rows per page", PAGE_SIZES, index=0, key="lx_ps")
        r2[4].markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        submitted = r2[4].form_submit_button("Search", use_container_width=True, type="primary", icon=":material/search:")
    if submitted:
        st.session_state["lx_page"] = 1
    page = st.session_state.get("lx_page", 1)

    params = {"page": page, "page_size": page_size, "order": order}
    if q.strip():
        params["q"] = q.strip()
    if types:
        params["event_type"] = ",".join(types)
    if sevs:
        params["severity"] = ",".join(sevs)
    if d_from:
        params["start"] = datetime.combine(d_from, time.min).isoformat()
    if d_to:
        params["end"] = datetime.combine(d_to, time(23, 59, 59)).isoformat()
    if d_from and d_to and d_from > d_to:
        st.markdown(notice("The start date is after the end date, so no events can match.", "warn"), unsafe_allow_html=True)

    with st.spinner("Searching events…"):
        res = api.fetch("/events", params, ttl=15)
    if not res.ok:
        show_api_error(res, "events")
    data = res.data
    stats, items, total = data["stats"], data["items"], data["total"]

    st.markdown(V.kpis(stats), unsafe_allow_html=True)
    panels = V.chart_panels(stats)
    c1, c2, c3 = st.columns([1.6, 1.1, 1.1])
    with c1, st.container(key="sxp_lx_day"):
        st.markdown(section_title("Events by day", "Daily event counts for the current filters (up to the latest 30 days with events). "
                                  "Uses the event timestamp, or the ingestion time when the event has none."), unsafe_allow_html=True)
        st.markdown(panels["day"], unsafe_allow_html=True)
    with c2, st.container(key="sxp_lx_type"):
        st.markdown(section_title("Event categories"), unsafe_allow_html=True)
        st.markdown(panels["type"], unsafe_allow_html=True)
    with c3, st.container(key="sxp_lx_sev"):
        st.markdown(section_title("Incident severity", "Events inherit the severity of the incident they belong to."),
                    unsafe_allow_html=True)
        st.markdown(panels["sev"], unsafe_allow_html=True)

    st.markdown(section_title("Event stream", right_html=f'<span class="sx-muted">{pager_text(page, page_size, total)}</span>'),
                unsafe_allow_html=True)
    st.markdown(V.event_rows(items), unsafe_allow_html=True)

    pages = max(1, math.ceil(total / page_size))
    nav = st.columns([1, 1, 4, 3])
    if nav[0].button("← Previous", key="lx_prev", disabled=page <= 1, use_container_width=True):
        st.session_state["lx_page"] = page - 1
        st.rerun()
    if nav[1].button("Next →", key="lx_next", disabled=page >= pages, use_container_width=True):
        st.session_state["lx_page"] = page + 1
        st.rerun()
    nav[2].markdown(f'<div class="sx-pager">Page {page} of {pages}</div>', unsafe_allow_html=True)

    linked = {}
    for e in items:
        if e.get("incident_id"):
            linked.setdefault(e["incident_id"], f'{(e.get("incident_severity") or "unscored").capitalize()} · {e.get("incident_title") or "Untitled"}')
    if linked:
        with nav[3]:
            pick = st.selectbox("Investigate an incident from these results", list(linked), key="lx_pick",
                                format_func=lambda i: linked[i][:60], label_visibility="collapsed")
        if st.button("Open selected incident in Investigation Center", key="lx_open", icon=":material/arrow_forward:"):
            st.session_state["selected_incident_id"] = pick
            st.switch_page("pages/3_Investigation_Center.py")

# =============================================================== INGEST
with tab_ingest:
    left, right = st.columns([1.5, 1])
    with left, st.container(key="sxp_lx_ingest"):
        st.markdown(section_title("Log ingestion", "Authorized security logs in CSV or JSON format."), unsafe_allow_html=True)
        uploaded = st.file_uploader("Drop a security log file", type=["csv", "json"], key="lx_file",
                                    help="Supported formats: CSV and JSON")
        if uploaded:
            st.caption(f"{uploaded.name} · {uploaded.size / 1024:.1f} KB")
            if st.button("Upload & analyze logs", key="lx_upload", type="primary", use_container_width=True,
                         icon=":material/upload:"):
                with st.spinner("Uploading and processing security events…"):
                    up = api.post("/logs/upload", files={"file": (uploaded.name, uploaded.getvalue(), "application/octet-stream")})
                if up.ok and isinstance(up.data, dict):
                    api.invalidate()
                    st.session_state["lx_upload_result"] = {
                        "incident_id": up.data.get("incident_id"), "events_count": up.data.get("events_count", 0),
                        "filename": uploaded.name, "investigation_id": None}
                elif up.reachable:
                    st.error(f"Upload failed ({up.status}): {up.error or 'unexpected response'}")
                else:
                    st.error("Could not reach the backend. Check the API connection in Settings.")

        # Rendered outside the upload button so the follow-up action survives Streamlit reruns.
        result = st.session_state.get("lx_upload_result")
        if result:
            st.success(f'Ingested {result["events_count"]} events from {result["filename"]}.')
            if result["incident_id"]:
                st.code(result["incident_id"], language="text")
                if not result["investigation_id"]:
                    if st.button("Start AI investigation", key="lx_start_inv", use_container_width=True,
                                 icon=":material/play_arrow:"):
                        with st.spinner("Starting the investigation workflow…"):
                            run = api.post(f'/investigations/{result["incident_id"]}/run')
                        if run.ok and isinstance(run.data, dict):
                            api.invalidate()
                            result["investigation_id"] = run.data.get("investigation_id") or "started"
                            st.session_state["lx_upload_result"] = result
                            st.rerun()
                        else:
                            st.error(f"Investigation could not be started: {run.error or 'backend unreachable'}")
                else:
                    st.success("Investigation request accepted. The agents are running.")
                    if st.button("Open in Investigation Center", key="lx_goto_inv", icon=":material/arrow_forward:"):
                        st.session_state["selected_incident_id"] = result["incident_id"]
                        st.switch_page("pages/3_Investigation_Center.py")
            else:
                st.markdown(notice("The upload was accepted but no incident was created.", "warn"), unsafe_allow_html=True)

    with right, st.container(key="sxp_lx_pipe"):
        st.markdown(section_title("Ingestion pipeline"), unsafe_allow_html=True)
        for n, (t, d) in enumerate([("Log upload", "Receive CSV or JSON security events."),
                                    ("Event processing", "Backend validates, hashes and stores each event."),
                                    ("Incident creation", "An incident record is created from the batch."),
                                    ("AI investigation", "The six-agent workflow analyses the incident.")], 1):
            st.markdown(f'<div class="sx-vt done"><span class="d"></span><div class="c"><div class="t"><b>{n:02d} · {t}</b></div>'
                        f'<div class="b">{d}</div></div></div>', unsafe_allow_html=True)
        st.markdown(section_title("Sample datasets"), unsafe_allow_html=True)
        samples = sorted(p for p in SAMPLE_DIR.glob("*") if p.suffix.lower() in (".csv", ".json")) if SAMPLE_DIR.exists() else []
        if samples:
            for p in samples:
                st.download_button(f"Download {p.name}", p.read_bytes(), file_name=p.name, key=f"lx_sample_{p.name}",
                                   use_container_width=True, icon=":material/download:")
        else:
            st.markdown(empty_state("No sample datasets found", "Place CSV or JSON files in the project's sample_data/ folder."),
                        unsafe_allow_html=True)
