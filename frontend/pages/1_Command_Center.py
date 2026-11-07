import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os

API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")

if 'token' not in st.session_state or not st.session_state['token']:
    st.warning("Please log in from the main page.")
    st.stop()

headers = {"Authorization": f"Bearer {st.session_state['token']}"}

st.title("Command Center")

@st.cache_data(ttl=60)
def fetch_incidents():
    try:
        response = requests.get(f"{API_URL}/incidents", headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception:
        return []

incidents = fetch_incidents()

if not incidents:
    st.info("No active incidents found.")
else:
    df = pd.DataFrame(incidents)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"<div class='metric-card'>Total Incidents<div class='metric-value'>{len(df)}</div></div>", unsafe_allow_html=True)
    with col2:
        open_count = len(df[df['status'] == 'open'])
        st.markdown(f"<div class='metric-card'>Open Incidents<div class='metric-value'>{open_count}</div></div>", unsafe_allow_html=True)
    with col3:
        critical = len(df[df['severity'] == 'critical'])
        st.markdown(f"<div class='metric-card' style='border-color: #EF4444;'>Critical<div class='metric-value' style='color: #EF4444;'>{critical}</div></div>", unsafe_allow_html=True)
    with col4:
        resolved = len(df[df['status'] == 'resolved'])
        st.markdown(f"<div class='metric-card' style='border-color: #10B981;'>Resolved<div class='metric-value' style='color: #10B981;'>{resolved}</div></div>", unsafe_allow_html=True)
        
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Incidents by Severity")
        if 'severity' in df.columns and not df['severity'].isnull().all():
            sev_counts = df['severity'].fillna('unknown').value_counts().reset_index()
            sev_counts.columns = ['Severity', 'Count']
            fig = px.pie(sev_counts, values='Count', names='Severity', hole=0.4, 
                         color_discrete_sequence=px.colors.sequential.Blues_r)
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No severity data available yet.")
            
    with col2:
        st.subheader("Recent Incidents")
        st.dataframe(df[['title', 'status', 'severity', 'created_at']].head(10), use_container_width=True)
