
import os
import time
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")

st.set_page_config(
    page_title="SENTINELX | Investigation Center",
    page_icon="🧠",
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
    <div class="small-label">SENTINELX / INCIDENT RESPONSE</div>
    <h1>🧠 Investigation Center</h1>
    <p>Manage security incidents and coordinate AI-powered investigations.</p>
</div>
""", unsafe_allow_html=True)

# Load incidents
try:
    with st.spinner("Loading incident records..."):
        response = requests.get(
            f"{API_URL}/incidents",
            headers=headers,
            timeout=20
        )

    if response.status_code != 200:
        st.error(
            f"Could not retrieve incidents. "
            f"Backend returned {response.status_code}: {response.text[:500]}"
        )
        st.stop()

    incidents = response.json()

    if not isinstance(incidents, list):
        st.error("Unexpected incident data received from the backend.")
        st.stop()

except requests.RequestException as e:
    st.error(f"Backend connection failed: {e}")
    st.stop()

if not incidents:
    st.info("No incidents found. Upload security logs in Log Explorer to create one.")
    st.stop()

# Incident selection
st.markdown("### 🎯 Select an Incident")

incident_options = {
    f"{item.get('title', 'Untitled Incident')} | "
    f"{item.get('status', 'Unknown')} | "
    f"{str(item.get('id', ''))[:8]}": item.get("id")
    for item in incidents
    if item.get("id")
}

if not incident_options:
    st.warning("No valid incident identifiers were returned.")
    st.stop()

selected_label = st.selectbox(
    "Choose an incident to investigate",
    options=list(incident_options.keys())
)

incident_id = incident_options[selected_label]

# Load incident details
try:
    with st.spinner("Retrieving incident details..."):
        details_response = requests.get(
            f"{API_URL}/incidents/{incident_id}",
            headers=headers,
            timeout=20
        )

    if details_response.status_code != 200:
        st.error(
            f"Could not load incident details: "
            f"{details_response.status_code} "
            f"{details_response.text[:500]}"
        )
        st.stop()

    details = details_response.json()

except requests.RequestException as e:
    st.error(f"Incident details request failed: {e}")
    st.stop()

title = details.get("title", "Untitled Incident")
status = details.get("status", "Unknown")
severity = details.get("severity", "Not assessed")
events = details.get("events") or []
events_count = details.get("events_count", len(events))

st.divider()

# Incident metrics
st.markdown("### 📊 Incident Overview")

m1, m2, m3, m4 = st.columns(4)

with m1:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">'
        f'INCIDENT STATUS</div><div class="metric-value">{status}</div></div>',
        unsafe_allow_html=True
    )

with m2:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">'
        f'SEVERITY</div><div class="metric-value">{severity}</div></div>',
        unsafe_allow_html=True
    )

with m3:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">'
        f'EVENTS</div><div class="metric-value">{events_count}</div></div>',
        unsafe_allow_html=True
    )

with m4:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">'
        f'INCIDENTS LOADED</div><div class="metric-value">'
        f'{len(incidents)}</div></div>',
        unsafe_allow_html=True
    )

st.markdown("### 🗂️ Incident Details")

st.markdown(
    f'<div class="panel"><div class="small-label">INCIDENT TITLE</div>'
    f'<h3>{title}</h3>'
    f'<div class="small-label">INCIDENT IDENTIFIER</div>'
    f'<code>{incident_id}</code></div>',
    unsafe_allow_html=True
)

# Raw event viewer
st.markdown("### 📋 Security Event Evidence")

if isinstance(events, list) and events:
    st.caption(f"Showing {len(events)} event records")

    with st.expander("Explore raw security events", expanded=False):
        st.dataframe(
            events,
            use_container_width=True,
            hide_index=True
        )
else:
    st.info("No raw event records are currently available for this incident.")

# Investigation controls
st.divider()
st.markdown("### ⚙️ Investigation Controls")

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("""
    <div class="panel">
        <h4>🧠 AI Investigation</h4>
        <p>Run the SENTINELX investigation workflow against this incident.</p>
        <p class="small-label">ACTION: RUN / RE-RUN</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button(
        "🚀 Run / Re-run Investigation",
        use_container_width=True
    ):
        try:
            with st.spinner("Triggering investigation workflow..."):
                run_response = requests.post(
                    f"{API_URL}/investigations/{incident_id}/run",
                    headers=headers,
                    timeout=60
                )

            if run_response.status_code in (200, 201, 202):
                st.success("Investigation request accepted successfully!")
                st.session_state["last_investigated_incident"] = incident_id
                st.json(run_response.json())
                st.info(
                    "Check Agent Operations for detailed agent results."
                )
            else:
                st.error(
                    f"Investigation request failed "
                    f"({run_response.status_code}): "
                    f"{run_response.text[:1000]}"
                )

        except requests.RequestException as e:
            st.error(f"Investigation request error: {e}")

with col2:
    st.markdown("""
    <div class="panel">
        <h4>🔎 Investigation Workflow</h4>
        <p>1. Incident context retrieval</p>
        <p>2. Security event analysis</p>
        <p>3. Agent-based investigation</p>
        <p>4. Findings and risk assessment</p>
        <p>5. Audit and response review</p>
        <p class="small-label">DETAILED OUTPUT: AGENT OPERATIONS</p>
    </div>
    """, unsafe_allow_html=True)

last_run = st.session_state.get("last_investigated_incident")

if last_run == incident_id:
    st.success("An investigation request was accepted for this incident in this session.")

st.divider()

st.markdown("### 🔗 Continue Investigation")
st.info(
    "Open Agent Operations to inspect the latest investigation report "
    "and individual agent outputs. Open Reports to review available summaries."
)

st.caption(
    "SENTINELX · Autonomous Incident Response Network · "
    "Evidence-backed defensive security investigation"
)
