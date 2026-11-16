import streamlit as st
import os

if 'token' not in st.session_state or not st.session_state['token']:
    st.warning("Please log in from the main page.")
    st.stop()

st.title("System Settings")

st.markdown("### Configuration")

st.text_input("API URL", value=os.getenv("API_URL", "http://localhost:8000/api/v1"), disabled=True)
st.text_input("n8n Webhook URL", value=os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/sentinelx"), disabled=True)

st.markdown("---")
st.markdown("### LLM Provider")
api_key = st.text_input("OpenAI API Key (Set in .env or via env vars for security)", value="**************", type="password", disabled=True)
st.info("API Keys should be managed securely via environment variables or secret managers, not the UI.")

st.markdown("---")
st.markdown("### About SENTINELX")
st.markdown("Version 1.0.0-hackathon")
st.markdown("Built with FastAPI, LangGraph, Streamlit, and n8n.")
