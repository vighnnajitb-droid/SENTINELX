import streamlit as st
import requests
import pandas as pd
import time
import os

API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")

if 'token' not in st.session_state or not st.session_state['token']:
    st.warning("Please log in from the main page.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state['token']}"}

st.title("Investigation Center")

# Fetch incidents
response = requests.get(f"{API_URL}/incidents", headers=headers)
if response.status_code == 200:
    incidents = response.json()
    if not incidents:
        st.info("No incidents found.")
    else:
        incident_opts = {f"{inc['title']} ({inc['status']})": inc['id'] for inc in incidents}
        selected_incident = st.selectbox("Select Incident to Investigate", options=list(incident_opts.keys()))
        
        if selected_incident:
            inc_id = incident_opts[selected_incident]
            
            # Fetch specific incident details
            inc_details_resp = requests.get(f"{API_URL}/incidents/{inc_id}", headers=headers)
            if inc_details_resp.status_code == 200:
                details = inc_details_resp.json()
                st.subheader("Incident Details")
                st.write(f"**Title:** {details['title']}")
                st.write(f"**Status:** {details['status']}")
                st.write(f"**Severity:** {details.get('severity', 'Not assessed')}")
                st.write(f"**Events Count:** {details['events_count']}")
                
                with st.expander("View Raw Events"):
                    st.dataframe(details['events'])
                    
                st.markdown("---")
                st.subheader("Manage Investigation")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Run / Re-run Investigation"):
                        resp = requests.post(f"{API_URL}/investigations/{inc_id}/run", headers=headers)
                        if resp.status_code == 200:
                            st.success("Investigation triggered!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Failed to run investigation.")
                
                # Fetch investigation status (just picking the latest if multiple)
                # In a real app we'd have a specific endpoint to list investigations for an incident
                # Here we will rely on generating reports or fetching the incident list which we mocked simply
                # To see agent results, user will go to Agent Operations or Reports.
                st.info("Navigate to 'Agent Operations' to see detailed step-by-step reasoning.")

else:
    st.error("Failed to fetch incidents.")
