
import os
import requests
import streamlit as st
import plotly.graph_objects as go

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")

st.set_page_config(
    page_title="SENTINELX | Risk Intelligence",
    page_icon="⚠️",
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
    font-size: 24px;
    font-weight: 700;
    margin-top: 6px;
}
.small-label {
    color: #91a8c4;
    font-size: 12px;
    letter-spacing: 1px;
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
    <div class="small-label">SENTINELX / SECURITY INTELLIGENCE</div>
    <h1>⚠️ Threat & Risk Intelligence</h1>
    <p>Analyze AI-generated risk classifications, confidence and supporting evidence.</p>
</div>
""", unsafe_allow_html=True)

# Fetch incidents
try:
    with st.spinner("Retrieving incident intelligence..."):
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
    st.info("No incidents available. Upload logs to begin risk analysis.")
    st.stop()

# Incident selector
incident_options = {
    f"{item.get('title', 'Untitled Incident')} "
    f"({str(item.get('id', ''))[:8]})": item.get("id")
    for item in incidents
    if item.get("id")
}

if not incident_options:
    st.warning("No valid incident identifiers found.")
    st.stop()

st.markdown("### 🎯 Select Incident")

selected_label = st.selectbox(
    "Choose an incident for risk analysis",
    options=list(incident_options.keys())
)

incident_id = incident_options[selected_label]

# Fetch report
try:
    with st.spinner("Analyzing available investigation reports..."):
        rep_resp = requests.get(
            f"{API_URL}/reports/{incident_id}",
            headers=headers,
            timeout=30
        )

    if rep_resp.status_code != 200:
        st.error(
            f"Report request failed ({rep_resp.status_code}): "
            f"{rep_resp.text[:500]}"
        )
        st.stop()

    report = rep_resp.json()

except requests.RequestException as e:
    st.error(f"Report retrieval failed: {e}")
    st.stop()

investigations = report.get("investigations", [])

if not investigations:
    st.warning("No investigations found for this incident.")
    st.info(
        "Run an investigation from Investigation Center, "
        "then return here to review its risk assessment."
    )
    st.stop()

latest_inv = investigations[-1]
agents = latest_inv.get("agents", {}) or {}
risk_data = agents.get("RiskAssessmentAgent")

st.markdown("### 📊 Risk Assessment Overview")

m1, m2, m3 = st.columns(3)

with m1:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">'
        f'INVESTIGATION STATUS</div><div class="metric-value">'
        f'{latest_inv.get("status", "Unknown")}</div></div>',
        unsafe_allow_html=True
    )

with m2:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">'
        f'INVESTIGATION COUNT</div><div class="metric-value">'
        f'{len(investigations)}</div></div>',
        unsafe_allow_html=True
    )

with m3:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">'
        f'RISK ASSESSMENT</div><div class="metric-value">'
        f'{"Available" if risk_data else "Pending"}</div></div>',
        unsafe_allow_html=True
    )

if not isinstance(risk_data, dict) or not risk_data:
    st.warning(
        "Risk Assessment Agent results are not available in the latest investigation."
    )
    st.info(
        "Check Agent Operations for investigation outputs. "
        "The dashboard will not invent missing risk scores."
    )
    st.stop()

# Read actual agent output
severity = str(risk_data.get("severity", "Unknown")).upper()
confidence = risk_data.get("confidence_score", 0)
justification = risk_data.get("justification", "No justification provided.")

try:
    confidence = float(confidence)
    if 0 <= confidence <= 1:
        confidence *= 100
    confidence = max(0, min(confidence, 100))
except (TypeError, ValueError):
    confidence = 0

severity_colors = {
    "CRITICAL": "#ef4444",
    "HIGH": "#f97316",
    "MEDIUM": "#eab308",
    "LOW": "#22c55e",
    "INFO": "#38bdf8"
}

severity_color = severity_colors.get(severity, "#94a3b8")

st.divider()
st.markdown("### 🚨 AI Risk Classification")

left, right = st.columns([1, 1.2])

with left:
    st.markdown(
        f'<div class="panel">'
        f'<div class="small-label">DETECTED SEVERITY</div>'
        f'<h1 style="color:{severity_color};">{severity}</h1>'
        f'<p>Classification returned by RiskAssessmentAgent</p>'
        f'</div>',
        unsafe_allow_html=True
    )

    st.markdown("#### 📝 Assessment Justification")
    st.markdown(
        f'<div class="panel">{justification}</div>',
        unsafe_allow_html=True
    )

with right:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=confidence,
            number={"suffix": "%", "font": {"size": 38, "color": "#f1f6ff"}},
            title={
                "text": "AI Confidence Score",
                "font": {"size": 18, "color": "#c5d5e8"}
            },
            gauge={
                "axis": {
                    "range": [0, 100],
                    "tickcolor": "#9eb2ca"
                },
                "bar": {"color": "#3b82f6"},
                "bgcolor": "#101b2b",
                "borderwidth": 1,
                "bordercolor": "#263e5d",
                "steps": [
                    {"range": [0, 40], "color": "#263447"},
                    {"range": [40, 80], "color": "#34465d"},
                    {"range": [80, 100], "color": "#42566d"}
                ]
            }
        )
    )

    fig.update_layout(
        height=300,
        paper_bgcolor="#101b2b",
        plot_bgcolor="#101b2b",
        font={"color": "#f1f6ff"},
        margin={"t": 60, "b": 20, "l": 30, "r": 30}
    )

    st.plotly_chart(fig, use_container_width=True)

# Full agent output
with st.expander("🔬 View complete Risk Assessment Agent output"):
    st.json(risk_data)

st.divider()

st.markdown("### 🛡️ Assessment Notes")
st.info(
    "Severity and confidence above are taken from the latest available "
    "RiskAssessmentAgent output. Confidence is not the same as the probability "
    "that an incident is malicious."
)

st.caption(
    "SENTINELX · Threat & Risk Intelligence · "
    "Evidence-backed defensive security"
)
