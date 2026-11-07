import streamlit as st
import requests
import json
import os

API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")

if 'token' not in st.session_state or not st.session_state['token']:
    st.warning("Please log in from the main page.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state['token']}"}

st.title("Incident Reports")

inc_resp = requests.get(f"{API_URL}/incidents", headers=headers)
if inc_resp.status_code == 200 and inc_resp.json():
    incidents = inc_resp.json()
    incident_opts = {f"{inc['title']} ({inc['id'][:8]})": inc['id'] for inc in incidents}
    selected_inc = st.selectbox("Select Incident for Report", options=list(incident_opts.keys()))
    
    if selected_inc:
        inc_id = incident_opts[selected_inc]
        if st.button("Generate Report"):
            with st.spinner("Generating full report..."):
                rep_resp = requests.get(f"{API_URL}/reports/{inc_id}", headers=headers)
                
                if rep_resp.status_code == 200:
                    report = rep_resp.json()
                    
                    st.success("Report Generated")
                    st.download_button(
                        label="Download JSON Report",
                        data=json.dumps(report, indent=2),
                        file_name=f"sentinelx_report_{inc_id[:8]}.json",
                        mime="application/json"
                    )
                    
                    st.subheader("Report Summary")
                    st.write(f"**Incident:** {report['incident']['title']}")
                    st.write(f"**Final Status:** {report['incident']['status']}")
                    st.write(f"**Overall Severity:** {report['incident']['severity']}")
                    
                    for i, inv in enumerate(report['investigations']):
                        with st.expander(f"Investigation Run {i+1} ({inv['status']})"):
                            st.json(inv['agents'])
                else:
                    st.error("Failed to generate report.")
else:
    st.info("No incidents available.")
