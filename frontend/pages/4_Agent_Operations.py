import streamlit as st
import requests
import json
import os

API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")

if 'token' not in st.session_state or not st.session_state['token']:
    st.warning("Please log in from the main page.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state['token']}"}

st.title("Agent Operations")
st.markdown("Inspect the output and reasoning of individual SENTINELX AI agents.")

# First select incident, then select investigation, then view agents
inc_resp = requests.get(f"{API_URL}/incidents", headers=headers)
if inc_resp.status_code == 200 and inc_resp.json():
    incidents = inc_resp.json()
    incident_opts = {f"{inc['title']} ({inc['id'][:8]})": inc['id'] for inc in incidents}
    selected_inc = st.selectbox("Select Incident", options=list(incident_opts.keys()))
    
    if selected_inc:
        inc_id = incident_opts[selected_inc]
        
        # We fetch reports to get the investigations for this incident
        rep_resp = requests.get(f"{API_URL}/reports/{inc_id}", headers=headers)
        if rep_resp.status_code == 200:
            report = rep_resp.json()
            investigations = report.get("investigations", [])
            
            if not investigations:
                st.info("No investigations have been run for this incident.")
            else:
                # We just pick the latest for display
                latest_inv = investigations[-1]
                st.subheader("Latest Investigation Agent Results")
                st.write(f"**Status:** {latest_inv.get('status')}")
                
                agents_data = latest_inv.get("agents", {})
                
                if agents_data:
                    tabs = st.tabs(list(agents_data.keys()))
                    for idx, (agent_name, output) in enumerate(agents_data.items()):
                        with tabs[idx]:
                            st.json(output)
                else:
                    st.info("Agent outputs are pending or investigation failed.")
else:
    st.info("No incidents available.")
