import streamlit as st
import requests
import pandas as pd
import os

API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")

if 'token' not in st.session_state or not st.session_state['token']:
    st.warning("Please log in from the main page.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state['token']}"}

st.title("Audit Trail")
st.markdown("Tamper-evident logs of all system and agent actions.")

inc_resp = requests.get(f"{API_URL}/incidents", headers=headers)
if inc_resp.status_code == 200 and inc_resp.json():
    incidents = inc_resp.json()
    incident_opts = {f"{inc['title']} ({inc['id'][:8]})": inc['id'] for inc in incidents}
    selected_inc = st.selectbox("Select Incident to Audit", options=list(incident_opts.keys()))
    
    if selected_inc:
        inc_id = incident_opts[selected_inc]
        audit_resp = requests.get(f"{API_URL}/incidents/{inc_id}/audit", headers=headers)
        
        if audit_resp.status_code == 200:
            logs = audit_resp.json()
            if logs:
                df = pd.DataFrame(logs)
                st.dataframe(
                    df[['timestamp', 'entity_type', 'action', 'current_hash']],
                    use_container_width=True
                )
                
                st.subheader("Raw Audit Details")
                selected_log = st.selectbox("Select Log Entry", options=range(len(logs)), format_func=lambda x: f"{logs[x]['timestamp']} - {logs[x]['action']}")
                st.json(logs[selected_log])
                
            else:
                st.info("No audit logs found for this incident.")
        else:
            st.error("Failed to fetch audit logs.")
else:
    st.info("No incidents available.")
