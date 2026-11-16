
import os
import json
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")

st.set_page_config(
    page_title="SENTINELX | Incident Reports",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background: #080f1c;
    color: #e5edf8;
}
.block-container {
    padding-top: 2rem;
    max-width: 1450px;
}
.hero {
    background: linear-gradient(120deg,#101f35,#142d49);
    padding: 25px;
    border: 1px solid #263e5d;
    border-radius: 14px;
    margin-bottom: 22px;
}
.hero h1 {
    color: #f1f6ff;
    margin-bottom: 5px;
}
.hero p {
    color: #9eb2ca;
    margin-bottom: 0;
}
.panel {
    background: #101b2b;
    border: 1px solid #243750;
    padding: 20px;
    border-radius: 12px;
    margin-bottom: 15px;
}
.metric-card {
    background: #101b2b;
    border: 1px solid #243750;
    border-radius: 11px;
    padding: 17px;
}
.metric-label {
    color: #91a8c4;
    font-size: 12px;
    letter-spacing: 1px;
}
.metric-value {
    color: #f1f6ff;
    font-size: 25px;
    font-weight: 700;
    margin-top: 5px;
}
.small-label {
    color: #91a8c4;
    font-size: 12px;
    letter-spacing: 1px;
}
div.stButton > button {
    background: #1677d2;
    color: white;
    border: 0;
    border-radius: 8px;
    min-height: 43px;
    font-weight: 600;
}
div.stButton > button:hover {
    background: #258ce9;
    color: white;
}
</style>
""", unsafe_allow_html=True)

if "token" not in st.session_state or not st.session_state["token"]:
    st.warning("Please log in from the main page.")
    st.stop()

headers = {
    "Authorization": f"Bearer {st.session_state['token']}"
}

st.markdown("""
<div class="hero">
    <div class="small-label">SENTINELX / REPORTING & ANALYTICS</div>
    <h1>📊 Incident Reporting Center</h1>
    <p>Generate, review and export evidence-backed security incident reports.</p>
</div>
""", unsafe_allow_html=True)

# Fetch incidents
try:
    with st.spinner("Loading incident records..."):
        inc_resp = requests.get(
            f"{API_URL}/incidents",
            headers=headers,
            timeout=20
        )

    if inc_resp.status_code != 200:
        st.error(
            f"Incident request failed ({inc_resp.status_code}): "
            f"{inc_resp.text[:500]}"
        )
        st.stop()

    incidents = inc_resp.json()

    if not isinstance(incidents, list):
        st.error("Unexpected incident data received.")
        st.stop()

except requests.RequestException as e:
    st.error(f"Backend connection failed: {e}")
    st.stop()

if not incidents:
    st.info("No incidents available. Upload logs to generate your first report.")
    st.stop()

incident_options = {
    f"{item.get('title', 'Untitled Incident')} "
    f"({str(item.get('id', ''))[:8]})": item.get("id")
    for item in incidents
    if item.get("id")
}

if not incident_options:
    st.warning("No valid incident identifiers found.")
    st.stop()

st.markdown("### 🎯 Report Configuration")

selected_label = st.selectbox(
    "Select incident for report generation",
    options=list(incident_options.keys())
)

incident_id = incident_options[selected_label]

if st.button("📄 Generate Incident Report", use_container_width=True):
    try:
        with st.spinner("Generating report from available investigation data..."):
            rep_resp = requests.get(
                f"{API_URL}/reports/{incident_id}",
                headers=headers,
                timeout=45
            )

        if rep_resp.status_code == 200:
            report = rep_resp.json()

            if not isinstance(report, dict):
                st.error("Unexpected report format received.")
                st.stop()

            st.session_state["generated_report"] = report
            st.session_state["generated_report_incident"] = incident_id
            st.success("Incident report retrieved successfully!")

        else:
            st.error(
                f"Report generation failed ({rep_resp.status_code}): "
                f"{rep_resp.text[:1000]}"
            )

    except requests.RequestException as e:
        st.error(f"Report request failed: {e}")

# Display report saved in this session
report = st.session_state.get("generated_report")
report_incident = st.session_state.get("generated_report_incident")

if report and report_incident == incident_id:
    incident = report.get("incident", {}) or {}
    investigations = report.get("investigations", []) or []

    if not isinstance(incident, dict):
        incident = {}

    if not isinstance(investigations, list):
        investigations = []

    st.divider()
    st.markdown("### 📊 Executive Summary")

    title = incident.get("title", "Untitled Incident")
    status = incident.get("status", "Unknown")
    severity = incident.get("severity", "Not assessed")
    events_count = incident.get("events_count", "Unavailable")

    m1, m2, m3, m4 = st.columns(4)

    with m1:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">'
            f'INCIDENT STATUS</div><div class="metric-value">'
            f'{status}</div></div>',
            unsafe_allow_html=True
        )

    with m2:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">'
            f'SEVERITY</div><div class="metric-value">'
            f'{severity}</div></div>',
            unsafe_allow_html=True
        )

    with m3:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">'
            f'EVENT COUNT</div><div class="metric-value">'
            f'{events_count}</div></div>',
            unsafe_allow_html=True
        )

    with m4:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">'
            f'INVESTIGATION RUNS</div><div class="metric-value">'
            f'{len(investigations)}</div></div>',
            unsafe_allow_html=True
        )

    st.markdown("### 🗂️ Incident Information")

    st.markdown(
        f'<div class="panel">'
        f'<div class="small-label">INCIDENT TITLE</div>'
        f'<h3>{title}</h3>'
        f'<div class="small-label">INCIDENT ID</div>'
        f'<code>{incident_id}</code>'
        f'</div>',
        unsafe_allow_html=True
    )

    st.divider()
    st.markdown("### 🧠 Investigation History")

    if investigations:
        for index, investigation in enumerate(investigations):
            if not isinstance(investigation, dict):
                continue

            inv_status = investigation.get("status", "Unknown")
            agents = investigation.get("agents", {}) or {}

            with st.expander(
                f"Investigation Run {index + 1} — {inv_status}",
                expanded=(index == len(investigations) - 1)
            ):
                st.write(f"**Status:** {inv_status}")

                if isinstance(agents, dict) and agents:
                    tabs = st.tabs(list(agents.keys()))

                    for tab, (agent_name, output) in zip(tabs, agents.items()):
                        with tab:
                            st.markdown(f"#### {agent_name}")
                            st.json(output)
                else:
                    st.info("No agent output is available for this run.")

    else:
        st.info("No investigation runs are recorded for this incident.")

    st.divider()
    st.markdown("### 📥 Export Report")

    report_json = json.dumps(report, indent=2, ensure_ascii=False)

    st.download_button(
        label="⬇️ Download Complete JSON Report",
        data=report_json,
        file_name=f"sentinelx_report_{incident_id[:8]}.json",
        mime="application/json",
        use_container_width=True
    )

    st.caption(
        "Export contains the report data returned by the SENTINELX backend."
    )

st.divider()

st.markdown("### 🛡️ Reporting Principles")
st.info(
    "Reports display incident and investigation information returned by the backend. "
    "Missing findings are shown as unavailable rather than invented."
)

st.caption(
    "SENTINELX · Incident Reporting & Analytics · "
    "Evidence-backed security intelligence"
)

