
import os
import requests
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

API_URL = os.getenv(
    "API_URL",
    "http://127.0.0.1:8000/api/v1"
)

# ---------------- PAGE CONFIG ----------------

st.set_page_config(
    page_title="SENTINELX | Command Center",
    page_icon="🛡️",
    layout="wide"
)

# ---------------- THEME ----------------

st.markdown("""
<style>
.stApp {
    background: #080E1B;
    color: #E6EDF7;
}
[data-testid="stSidebar"] {
    background: #0B1425;
    border-right: 1px solid #1D2B42;
}
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}
h1, h2, h3 {
    color: #E6EDF7 !important;
}
.soc-header {
    background: linear-gradient(110deg, #101F38, #102B42);
    border: 1px solid #24415E;
    border-radius: 14px;
    padding: 24px;
    margin-bottom: 22px;
}
.soc-subtitle {
    color: #9DB1CA;
    font-size: 14px;
}
.metric-card {
    background: #111C30;
    border: 1px solid #263B59;
    border-radius: 12px;
    padding: 18px;
    min-height: 112px;
}
.metric-label {
    color: #9DB1CA;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 1px;
}
.metric-value {
    color: #F1F6FF;
    font-size: 32px;
    font-weight: 750;
    margin-top: 8px;
}
.agent-card {
    background: #111C30;
    border: 1px solid #263B59;
    border-radius: 10px;
    padding: 15px;
    min-height: 90px;
}
.agent-name {
    color: #E6EDF7;
    font-weight: 650;
}
.agent-description {
    color: #91A6C1;
    font-size: 12px;
    margin-top: 5px;
}
div.stButton > button {
    background: #123C59;
    color: white;
    border: 1px solid #27749B;
    border-radius: 8px;
}
div.stButton > button:hover {
    background: #176184;
    color: white;
    border-color: #36B7E9;
}
</style>
""", unsafe_allow_html=True)

# ---------------- AUTHENTICATION ----------------

if "token" not in st.session_state or not st.session_state["token"]:
    st.warning("Please log in from the main page.")
    st.stop()

headers = {
    "Authorization": f"Bearer {st.session_state['token']}"
}

# ---------------- HEADER ----------------

header_col1, header_col2 = st.columns([4, 1])

with header_col1:
    st.markdown("""
    <div class="soc-header">
        <h1>🛡️ SENTINELX</h1>
        <div class="soc-subtitle">
            AUTONOMOUS INCIDENT RESPONSE NETWORK
        </div>
        <h3>Security Operations Command Center</h3>
        <div class="soc-subtitle">
            Detect. Investigate. Verify. Respond.
        </div>
    </div>
    """, unsafe_allow_html=True)

with header_col2:
    st.write("")
    st.write("")
    if st.button("↻ Refresh Data", use_container_width=True):
        st.rerun()

# ---------------- INCIDENT FETCH ----------------

@st.cache_data(ttl=30)
def fetch_incidents(api_url, token):
    try:
        response = requests.get(
            f"{api_url}/incidents",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15
        )

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                return data, None
            return [], "Unexpected API response format."

        return [], f"API returned HTTP {response.status_code}"

    except requests.RequestException as error:
        return [], str(error)

incidents, api_error = fetch_incidents(
    API_URL,
    st.session_state["token"]
)

if api_error:
    st.error(f"Backend connection issue: {api_error}")

df = pd.DataFrame(incidents)

# ---------------- METRICS ----------------

st.markdown("### Operational Overview")

if not df.empty:
    status = (
        df["status"].fillna("").str.lower()
        if "status" in df.columns
        else pd.Series(dtype=str)
    )

    severity = (
        df["severity"].fillna("").str.lower()
        if "severity" in df.columns
        else pd.Series(dtype=str)
    )

    total = len(df)
    open_count = int((status == "open").sum())
    critical = int((severity == "critical").sum())
    resolved = int((status == "resolved").sum())
else:
    total = open_count = critical = resolved = 0

metrics = [
    ("TOTAL INCIDENTS", total, "#56B4F7"),
    ("OPEN INCIDENTS", open_count, "#FBBF24"),
    ("CRITICAL ALERTS", critical, "#F87171"),
    ("RESOLVED", resolved, "#4ADE80")
]

cols = st.columns(4)

for col, (label, value, color) in zip(cols, metrics):
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value" style="color:{color}">
                {value}
            </div>
        </div>
        """, unsafe_allow_html=True)

st.write("")

# ---------------- INCIDENT ANALYTICS ----------------

st.markdown("### Threat Intelligence Overview")

chart_col, activity_col = st.columns([1, 1])

with chart_col:
    st.markdown("#### Incident Severity")

    if not df.empty and "severity" in df.columns:
        severity_data = (
            df["severity"]
            .fillna("Unknown")
            .str.title()
            .value_counts()
            .reset_index()
        )
        severity_data.columns = ["Severity", "Count"]

        fig = px.pie(
            severity_data,
            names="Severity",
            values="Count",
            hole=0.65,
            color_discrete_sequence=[
                "#F87171",
                "#FBBF24",
                "#56B4F7",
                "#4ADE80",
                "#94A3B8"
            ]
        )

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#E6EDF7",
            legend_title_text="Severity",
            margin=dict(t=20, b=20, l=10, r=10)
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Incident severity analytics will appear when data is available.")

with activity_col:
    st.markdown("#### Recent Incidents")

    if not df.empty:
        display_columns = [
            column for column in
            ["title", "status", "severity", "created_at"]
            if column in df.columns
        ]

        if display_columns:
            st.dataframe(
                df[display_columns].head(10),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No displayable incident fields found.")
    else:
        st.info("No incidents recorded yet.")

# ---------------- AGENT OPERATIONS ----------------

st.markdown("---")
st.markdown("### AI Agent Network")

st.caption(
    "Six specialized agents coordinate the defensive incident response workflow."
)

agents = [
    ("01", "Detection Agent", "Security event analysis"),
    ("02", "Investigation Agent", "Incident investigation"),
    ("03", "Threat Intelligence Agent", "Threat context enrichment"),
    ("04", "Risk Assessment Agent", "Severity and risk evaluation"),
    ("05", "Audit Agent", "Evidence and audit verification"),
    ("06", "Response Agent", "Human-approved response workflows")
]

agent_cols = st.columns(3)

for index, (number, name, description) in enumerate(agents):
    with agent_cols[index % 3]:
        st.markdown(f"""
        <div class="agent-card">
            <div class="agent-name">
                {number} &nbsp; {name}
            </div>
            <div class="agent-description">
                {description}
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.write("")

# ---------------- INCIDENT EXPLORER ----------------

st.markdown("---")
st.markdown("### Incident Explorer")

if not df.empty:
    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:
        if "severity" in df.columns:
            severity_options = ["All"] + sorted(
                df["severity"].fillna("Unknown").unique().tolist()
            )
            selected_severity = st.selectbox(
                "Filter by severity",
                severity_options
            )
        else:
            selected_severity = "All"

    with filter_col2:
        if "status" in df.columns:
            status_options = ["All"] + sorted(
                df["status"].fillna("Unknown").unique().tolist()
            )
            selected_status = st.selectbox(
                "Filter by status",
                status_options
            )
        else:
            selected_status = "All"

    filtered_df = df.copy()

    if selected_severity != "All" and "severity" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["severity"].fillna("Unknown") == selected_severity
        ]

    if selected_status != "All" and "status" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["status"].fillna("Unknown") == selected_status
        ]

    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Your incident explorer is ready. No incident records are currently available.")

# ---------------- FOOTER ----------------

st.markdown("---")

st.caption(
    f"SENTINELX SOC | Last dashboard render: "
    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
    "Defensive security monitoring"
)
