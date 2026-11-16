import os
from pathlib import Path
import streamlit as st

st.set_page_config(
    page_title="SENTINELX | Settings",
    page_icon="⚙️",
    layout="wide",
)

# Shared visual system
_theme_file = Path(__file__).resolve().parents[1] / "theme.css"
try:
    st.markdown(f"<style>{_theme_file.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
except OSError:
    pass

if not st.session_state.get("token"):
    st.warning("Please log in from the main page.")
    st.stop()

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")
N8N_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/sentinelx")

st.markdown("""
<div class="hero">
  <div class="small-label">SENTINELX / PLATFORM CONTROL</div>
  <h1>System Settings</h1>
  <p>Review runtime configuration and security boundaries for this workspace.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("### Runtime configuration")
a, b = st.columns(2)
with a:
    st.markdown('<div class="panel"><div class="metric-label">BACKEND API</div></div>', unsafe_allow_html=True)
    st.text_input("API base URL", value=API_URL, disabled=True, help="Configured through the API_URL environment variable.")
with b:
    st.markdown('<div class="panel"><div class="metric-label">WORKFLOW AUTOMATION</div></div>', unsafe_allow_html=True)
    st.text_input("n8n webhook URL", value=N8N_URL, disabled=True, help="Configured through the N8N_WEBHOOK_URL environment variable.")

st.divider()
st.markdown("### Security configuration")
left, right = st.columns([1.15, 1])
with left:
    st.markdown("""
    <div class="panel">
      <h4>Credential handling</h4>
      <p>Secrets and provider keys are intentionally not displayed in this interface.</p>
      <p>Manage API keys, database credentials, JWT signing secrets and integration tokens through your deployment environment or secret manager.</p>
    </div>
    """, unsafe_allow_html=True)
with right:
    st.markdown("""
    <div class="panel">
      <h4>Access controls</h4>
      <p>Workspace pages require an authenticated session.</p>
      <p>Consequential response actions should remain subject to human review and approval.</p>
    </div>
    """, unsafe_allow_html=True)

st.divider()
st.markdown("### Platform information")
x, y, z = st.columns(3)
with x:
    st.metric("VERSION", "1.0.0-hackathon")
with y:
    st.metric("FRONTEND", "Streamlit")
with z:
    st.metric("ORCHESTRATION", "LangGraph + n8n")

st.caption("SENTINELX · Autonomous Incident Response Network · Configuration values are read-only in this interface.")
