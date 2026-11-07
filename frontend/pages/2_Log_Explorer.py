import streamlit as st
import requests
import pandas as pd
import os

API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")

if 'token' not in st.session_state or not st.session_state['token']:
    st.warning("Please log in from the main page.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state['token']}"}

st.title("Log Explorer")

st.markdown("Upload raw security logs (CSV or JSON) to initiate a new analysis.")

uploaded_file = st.file_uploader("Choose a file", type=['csv', 'json'])

if uploaded_file is not None:
    if st.button("Upload and Analyze"):
        with st.spinner("Uploading and processing logs..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/plain")}
            response = requests.post(f"{API_URL}/logs/upload", headers=headers, files=files)
            
            if response.status_code == 200:
                data = response.json()
                st.success(f"Logs uploaded successfully! {data.get('events_count')} events processed.")
                incident_id = data.get("incident_id")
                st.info(f"Incident ID created: {incident_id}")
                
                # Start investigation automatically
                with st.spinner("Initiating AI investigation..."):
                    inv_response = requests.post(f"{API_URL}/investigations/{incident_id}/run", headers=headers)
                    if inv_response.status_code == 200:
                        st.success("Investigation started successfully. Head to Investigation Center to view progress.")
                    else:
                        st.error("Failed to start investigation automatically.")
            else:
                st.error(f"Failed to upload logs: {response.text}")

st.markdown("---")
st.subheader("Sample Datasets")
st.markdown("""
For demonstration purposes, you can use the provided synthetic datasets in the `sample_data/` directory:
- `normal_activity.csv`: Baseline traffic.
- `suspicious_activity.csv`: Contains brute-force and exfiltration attempts.
- `mixed_activity.csv`: A realistic mix of normal and malicious behavior.
""")
