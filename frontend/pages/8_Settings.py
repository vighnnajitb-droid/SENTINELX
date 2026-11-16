
import streamlit as st
import os
from pathlib import Path

st.set_page_config(
    page_title="SENTINELX | Settings",
    page_icon="⚙️",
    layout="wide"
)

# Load shared theme
theme_file = Path(__file__).resolve().parents[1] / "theme.css"

try:
    st.markdown(
        f"<style>{theme_file.read_text(encoding='utf-8')}</style>",
        unsafe_allow_html=True
    )
except OSError:
    pass

# Settings page styling
st.markdown("""
<style>
.settings-hero {
    background: linear-gradient(120deg, #101D33, #123451);
    border: 1px solid #285276;
    border-radius: 16px;
    padding: 25px;
    margin-bottom: 24px;
}
.settings-hero h1 {
    color: #EAF6FF;
    margin: 0;
    font-size: 30px;
}
.settings-hero p {
    color: #9CB8D5;
    margin: 8px 0 0 0;
}
.settings-card {
    background: linear-gradient(145deg, #111D30, #15243B);
    border: 1px solid #263E5C;
    border-radius: 14px;
    padding: 20px;
    margin-bottom: 15px;
}
.settings-label {
    color: #72CFFF;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
}
.settings-value {
    color: #E5EDF8;
    font-size: 15px;
    margin-top: 9px;
    overflow-wrap: anywhere;
}
.settings-muted {
    color: #91A6C1;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)

# Authentication
if not st.session_state.get("token"):
    st.warning("Please log in from the main page.")
    st.stop()

# Header
st.markdown("""
<div class="settings-hero">
    <h1>⚙️ SYSTEM SETTINGS</h1>
    <p>SENTINELX | Platform configuration and system information</p>
</div>
""", unsafe_allow_html=True)

# Configuration
st.subheader("Platform Configuration")

api_url = os.getenv(
    "API_URL",
    "http://localhost:8000/api/v1"
)

n8n_url = os.getenv(
    "N8N_WEBHOOK_URL",
    "http://localhost:5678/webhook/sentinelx"
)

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="settings-card">
        <div class="settings-label">Backend API</div>
        <div class="settings-value">FastAPI Service</div>
        <div class="settings-muted">Authenticated API connection</div>
    </div>
    """, unsafe_allow_html=True)

    st.text_input(
        "API URL",
        value=api_url,
        disabled=True
    )

with col2:
    st.markdown("""
    <div class="settings-card">
        <div class="settings-label">Workflow Engine</div>
        <div class="settings-value">n8n Automation</div>
        <div class="settings-muted">Workflow and agent integrations</div>
    </div>
    """, unsafe_allow_html=True)

    st.text_input(
        "n8n Webhook URL",
        value=n8n_url,
        disabled=True
    )

st.divider()

# Security
st.subheader("Security & Credentials")

st.markdown("""
<div class="settings-card">
    <div class="settings-label">Credential Management</div>
    <div class="settings-value">Environment-based configuration</div>
    <div class="settings-muted">
        API keys and secrets should be configured through environment
        variables or secure secret management.
    </div>
</div>
""", unsafe_allow_html=True)

st.info(
    "Credentials are not editable or displayed on this page. "
    "Never place API keys directly in frontend code."
)

st.divider()

# System information
st.subheader("Platform Information")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Version", "1.0.0")

with col2:
    st.metric("Frontend", "Streamlit")

with col3:
    st.metric("Architecture", "Multi-Agent AI")

st.markdown("""
<div class="settings-card">
    <div class="settings-label">Technology Stack</div>
    <div class="settings-value">
        FastAPI · LangGraph · Streamlit · PostgreSQL · n8n
    </div>
    <div class="settings-muted">
        SENTINELX — Autonomous Incident Response Network
    </div>
</div>
""", unsafe_allow_html=True)

st.caption("SENTINELX | System Configuration Console")
