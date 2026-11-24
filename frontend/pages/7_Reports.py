"""Reports: generate and export an incident report from real backend data.

Data: GET /incidents/{id}, /incidents/{id}/investigations, /audit?incident_id=,
and the original GET /reports/{id} (kept inside the JSON export for compatibility).
Exports: JSON (as before, now with the full report), Markdown, printable HTML.
"""
import streamlit as st

from sentinelx_ui import api, reporting
from sentinelx_ui.navigation import header, page_setup, show_api_error
from sentinelx_ui.views import reports as V
from sentinelx_ui.widgets import empty_state, notice, section_title

page_setup("Reports", "📄")
header("Reports", "Generate an evidence-based incident report and export it.", eyebrow="INTELLIGENCE / REPORTS")

inc = api.incident_list()
if not inc.ok:
    show_api_error(inc, "incidents")
incidents = [i for i in (inc.data or []) if i.get("id")]
if not incidents:
    st.markdown(empty_state("No incidents to report on", "Upload logs in the Log Explorer to create an incident."), unsafe_allow_html=True)
    st.stop()

labels = {i["id"]: f'{(i.get("severity") or "unscored").capitalize()} · {i.get("title") or "Untitled"} · {i["id"][:8]}' for i in incidents}
goto = st.session_state.pop("selected_incident_id", None)
if goto in labels:
    st.session_state["rp_pick"] = goto

row = st.columns([4, 1.4])
incident_id = row[0].selectbox("Incident", list(labels), key="rp_pick", format_func=lambda i: labels[i], label_visibility="collapsed")
if row[1].button("Generate report", key="rp_gen", type="primary", use_container_width=True, icon=":material/description:"):
    with st.spinner("Collecting incident, investigation and audit data…"):
        d = api.fetch(f"/incidents/{incident_id}", ttl=0, force=True)
        v = api.fetch(f"/incidents/{incident_id}/investigations", ttl=0, force=True)
        a = api.fetch("/audit", {"incident_id": incident_id, "page_size": 200}, ttl=0, force=True)
        legacy = api.fetch(f"/reports/{incident_id}", ttl=0, force=True)
    failed = next((x for x in (d, v) if not x.ok), None)
    if failed:
        show_api_error(failed, "the incident report data", stop=False)
    else:
        st.session_state["rp_report"] = reporting.build_report(
            d.data, v.data["investigations"], a.data if a.ok else None, legacy.data if legacy.ok else None)
        st.session_state["rp_report_for"] = incident_id

report = st.session_state.get("rp_report")
if not report:
    st.markdown(empty_state("No report generated yet", "Select an incident and choose “Generate report”. The report is built only from recorded backend data."),
                unsafe_allow_html=True)
    st.stop()

if st.session_state.get("rp_report_for") != incident_id:
    st.markdown(notice(f'Showing the report generated for “{report["incident"].get("title")}”. Generate again to switch to the selected incident.', "warn"),
                unsafe_allow_html=True)

name = (st.session_state.get("rp_report_for") or "incident")[:8]
ex = st.columns([1, 1, 1, 3])
ex[0].download_button("Export JSON", reporting.to_json(report), file_name=f"sentinelx_report_{name}.json", mime="application/json",
                      use_container_width=True, key="rp_json", icon=":material/data_object:")
ex[1].download_button("Export Markdown", reporting.to_markdown(report), file_name=f"sentinelx_report_{name}.md", mime="text/markdown",
                      use_container_width=True, key="rp_md", icon=":material/article:")
ex[2].download_button("Export HTML", reporting.to_html(report), file_name=f"sentinelx_report_{name}.html", mime="text/html",
                      use_container_width=True, key="rp_html", icon=":material/print:")
ex[3].markdown('<div class="sx-pager">Open the HTML export and use your browser’s Print → Save as PDF for a PDF copy.</div>', unsafe_allow_html=True)

st.markdown(V.header_kpis(report), unsafe_allow_html=True)
s = V.sections(report)
left, right = st.columns([2.1, 1])
with left:
    with st.container(key="sxp_rp_summary"):
        st.markdown(section_title(report["incident"].get("title") or "Incident report", "Composed from recorded facts only."), unsafe_allow_html=True)
        st.markdown('<div class="sx-sub" style="margin-top:0">Executive summary</div>' + s["summary"], unsafe_allow_html=True)
    with st.container(key="sxp_rp_findings"):
        st.markdown(section_title("Investigation findings"), unsafe_allow_html=True)
        st.markdown(s["findings"], unsafe_allow_html=True)
    with st.container(key="sxp_rp_agents"):
        st.markdown(section_title("Agent findings"), unsafe_allow_html=True)
        st.markdown(s["agents"], unsafe_allow_html=True)
    with st.container(key="sxp_rp_timeline"):
        st.markdown(section_title("Incident timeline"), unsafe_allow_html=True)
        st.markdown(s["timeline"], unsafe_allow_html=True)
with right:
    with st.container(key="sxp_rp_details"):
        st.markdown(section_title("Incident details"), unsafe_allow_html=True)
        st.markdown(s["details"], unsafe_allow_html=True)
    with st.container(key="sxp_rp_risk"):
        st.markdown(section_title("Risk assessment & response"), unsafe_allow_html=True)
        st.markdown(s["risk"], unsafe_allow_html=True)
    with st.container(key="sxp_rp_evidence"):
        st.markdown(section_title("Evidence summary"), unsafe_allow_html=True)
        st.markdown(s["evidence"], unsafe_allow_html=True)
        st.markdown(section_title("Audit"), unsafe_allow_html=True)
        st.markdown(s["audit"], unsafe_allow_html=True)
