import streamlit as st
import requests
import plotly.graph_objects as go
import os

API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")

if 'token' not in st.session_state or not st.session_state['token']:
    st.warning("Please log in from the main page.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state['token']}"}

st.title("Risk Assessment Dashboard")

inc_resp = requests.get(f"{API_URL}/incidents", headers=headers)
if inc_resp.status_code == 200 and inc_resp.json():
    incidents = inc_resp.json()
    incident_opts = {f"{inc['title']} ({inc['id'][:8]})": inc['id'] for inc in incidents}
    selected_inc = st.selectbox("Select Incident for Risk Analysis", options=list(incident_opts.keys()))
    
    if selected_inc:
        inc_id = incident_opts[selected_inc]
        rep_resp = requests.get(f"{API_URL}/reports/{inc_id}", headers=headers)
        
        if rep_resp.status_code == 200:
            report = rep_resp.json()
            investigations = report.get("investigations", [])
            
            if investigations:
                latest_inv = investigations[-1]
                agents = latest_inv.get("agents", {})
                risk_data = agents.get("RiskAssessmentAgent")
                
                if risk_data:
                    severity = risk_data.get("severity", "unknown").upper()
                    confidence = risk_data.get("confidence_score", 0)
                    justification = risk_data.get("justification", "N/A")
                    
                    st.markdown(f"### Severity: **{severity}**")
                    st.markdown(f"**Justification:** {justification}")
                    
                    fig = go.Figure(go.Indicator(
                        mode = "gauge+number",
                        value = confidence * 100,
                        title = {'text': "AI Confidence Score"},
                        gauge = {
                            'axis': {'range': [None, 100]},
                            'bar': {'color': "#3B82F6"},
                            'steps': [
                                {'range': [0, 40], 'color': "lightgray"},
                                {'range': [40, 80], 'color': "gray"}
                            ]
                        }
                    ))
                    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
                    st.plotly_chart(fig)
                else:
                    st.info("Risk Assessment hasn't been completed yet for this investigation.")
            else:
                st.info("No investigations found.")
else:
    st.info("No incidents available.")
