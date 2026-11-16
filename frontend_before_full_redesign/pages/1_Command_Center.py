
import os
import requests
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")

# ---------------- PAGE CONFIG ----------------

st.set_page_config(
    page_title="SENTINELX | Command Center",
    page_icon="🛡️",
    layout="wide"
)

# ---------------- PREMIUM SOC THEME ----------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Orbitron:wght@500;600;700;800&display=swap');

.stApp {
    background:
        radial-gradient(ellipse at 5% 0%, rgba(0,140,255,.12), transparent 35%),
        radial-gradient(ellipse at 95% 90%, rgba(0,220,255,.07), transparent 35%),
        #070D18;
    color: #EAF2FF;
    font-family: 'Inter', sans-serif;
}

header[data-testid="stHeader"] {
    background: rgba(7,13,24,.8);
}

.block-container {
    max-width: 1550px;
    padding-top: 2rem;
    padding-bottom: 3rem;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#0D192B,#080F1D);
    border-right: 1px solid #1D3552;
}

h1, h2, h3, h4 {
    color: #F0F6FF !important;
    font-family: 'Inter', sans-serif;
}

p, label, .stCaption {
    color: #9CB0C9;
}

.soc-header {
    position: relative;
    overflow: hidden;
    background: linear-gradient(115deg,#102642,#0B1B30 75%);
    border: 1px solid #285071;
    border-radius: 19px;
    padding: 30px;
    margin-bottom: 25px;
    box-shadow: 0 12px 40px rgba(0,0,0,.22);
}

.soc-header:after {
    content: "";
    position: absolute;
    width: 230px;
    height: 230px;
    right: -65px;
    top: -115px;
    border-radius: 50%;
    border: 1px solid rgba(43,190,255,.25);
    box-shadow: 0 0 0 30px rgba(43,190,255,.025),
                0 0 0 60px rgba(43,190,255,.02);
}

.brand {
    font-family: 'Orbitron', sans-serif;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 4px;
    color: #40C7FF;
    margin-bottom: 13px;
}

.soc-title {
    font-family: 'Orbitron', sans-serif;
    font-size: clamp(25px,3vw,38px);
    font-weight: 800;
    letter-spacing: 1px;
    color: #F2F7FF;
    margin-bottom: 10px;
}

.soc-title span {
    color: #32BFFF;
}

.soc-subtitle {
    color: #A2B8D2;
    font-size: 13px;
    line-height: 1.8;
}

.live-pill {
    display: inline-block;
    background: rgba(22,190,135,.10);
    border: 1px solid rgba(54,229,162,.35);
    border-radius: 30px;
    padding: 7px 13px;
    color: #52E5AE;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}

.section-heading {
    color: #EAF3FF;
    font-size: 19px;
    font-weight: 750;
    margin-top: 25px;
    margin-bottom: 5px;
}

.section-caption {
    color: #829AB7;
    font-size: 12px;
    margin-bottom: 17px;
}

.metric-card {
    position: relative;
    overflow: hidden;
    background: linear-gradient(145deg,#12233A,#0C1728);
    border: 1px solid #233F5E;
    border-radius: 15px;
    padding: 19px;
    min-height: 135px;
    box-shadow: 0 8px 25px rgba(0,0,0,.14);
    transition: all .2s ease;
}

.metric-card:hover {
    border-color: #32BFFF;
    transform: translateY(-3px);
}

.metric-label {
    color: #91A9C5;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.4px;
}

.metric-value {
    font-size: 34px;
    font-weight: 800;
    margin-top: 13px;
    line-height: 1.1;
}

.metric-note {
    color: #708AA8;
    font-size: 10px;
    margin-top: 9px;
}

.metric-accent {
    position: absolute;
    width: 75px;
    height: 75px;
    border-radius: 50%;
    right: -25px;
    bottom: -35px;
    opacity: .10;
}

.panel {
    background: linear-gradient(145deg,#101F33,#0B1728);
    border: 1px solid #203A58;
    border-radius: 15px;
    padding: 18px;
    min-height: 100px;
}

.panel-title {
    color: #E8F2FF;
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 5px;
}

.panel-caption {
    color: #829AB7;
    font-size: 11px;
}

.agent-card {
    background: linear-gradient(145deg,#12243A,#0C1829);
    border: 1px solid #23415F;
    border-radius: 13px;
    padding: 17px;
    min-height: 125px;
    transition: all .2s ease;
}

.agent-card:hover {
    border-color: #31BFFF;
    transform: translateY(-3px);
}

.agent-number {
    color: #36BFFF;
    font-family: 'Orbitron', sans-serif;
    font-size: 11px;
    letter-spacing: 2px;
    margin-bottom: 10px;
}

.agent-name {
    color: #EAF3FF;
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 7px;
}

.agent-description {
    color: #8EA6C1;
    font-size: 11px;
    line-height: 1.6;
}

.status-strip {
    background: rgba(12,29,48,.8);
    border: 1px solid #1E3C5B;
    border-radius: 12px;
    padding: 14px 17px;
    color: #A7BED7;
    font-size: 11px;
}

div.stButton > button {
    background: linear-gradient(100deg,#087BC5,#12A9E9);
    color: white;
    border: 1px solid #25B9F5;
    border-radius: 9px;
    min-height: 42px;
    font-weight: 700;
    transition: .2s ease;
}

div.stButton > button:hover {
    background: linear-gradient(100deg,#139CE9,#26C4FF);
    color: white;
    border-color: #70DFFF;
}

.stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
    background: #0B192B;
    color: #EAF3FF;
    border-color: #294765;
    border-radius: 8px;
}

[data-testid="stDataFrame"] {
    border: 1px solid #203A58;
    border-radius: 10px;
    overflow: hidden;
}

div[data-testid="stMetric"] {
    background: #101F33;
    border: 1px solid #203A58;
    border-radius: 12px;
    padding: 12px;
}

hr {
    border-color: #203A58;
}

.footer {
    text-align: center;
    color: #607B99;
    font-size: 10px;
    letter-spacing: 1.5px;
    padding-top: 25px;
}
</style>
""", unsafe_allow_html=True)


# ---------------- AUTHENTICATION ----------------

if "token" not in st.session_state or not st.session_state["token"]:
    st.warning("Please log in from the main page.")
    st.stop()

TOKEN = st.session_state["token"]

headers = {
    "Authorization": f"Bearer {TOKEN}"
}


# ---------------- HEADER ----------------

header_col1, header_col2 = st.columns([5, 1])

with header_col1:
    st.markdown("""
    <div class="soc-header">
        <div class="brand">SENTINELX / SECURITY OPERATIONS</div>
        <div class="soc-title">COMMAND <span>CENTER</span></div>
        <div class="soc-subtitle">
            Autonomous Incident Response Network<br>
            Detect. Investigate. Verify. Respond.
        </div>
    </div>
    """, unsafe_allow_html=True)

with header_col2:
    st.write("")
    st.write("")
    st.markdown(
        '<div class="live-pill">● SYSTEM ACCESS</div>',
        unsafe_allow_html=True
    )
    if st.button("↻ Refresh Data", use_container_width=True):
        st.cache_data.clear()
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


incidents, api_error = fetch_incidents(API_URL, TOKEN)

if api_error:
    st.error(f"Backend connection issue: {api_error}")

df = pd.DataFrame(incidents)


# ---------------- METRIC CALCULATIONS ----------------

if not df.empty:
    status_series = (
        df["status"].fillna("").astype(str).str.lower()
        if "status" in df.columns
        else pd.Series("", index=df.index)
    )

    severity_series = (
        df["severity"].fillna("").astype(str).str.lower()
        if "severity" in df.columns
        else pd.Series("", index=df.index)
    )

    total = len(df)
    open_count = int((status_series == "open").sum())
    critical = int((severity_series == "critical").sum())
    resolved = int((status_series == "resolved").sum())
else:
    total = open_count = critical = resolved = 0


# ---------------- OPERATIONAL OVERVIEW ----------------

st.markdown(
    '<div class="section-heading">Operational Overview</div>'
    '<div class="section-caption">Incident metrics and current workload</div>',
    unsafe_allow_html=True
)

metrics = [
    ("TOTAL INCIDENTS", total, "#4DBBFF", "All recorded incidents"),
    ("OPEN INCIDENTS", open_count, "#FBBF24", "Awaiting resolution"),
    ("CRITICAL ALERTS", critical, "#FB7185", "Critical severity records"),
    ("RESOLVED", resolved, "#4ADE80", "Successfully resolved")
]

metric_cols = st.columns(4)

for col, (label, value, color, note) in zip(metric_cols, metrics):
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value" style="color:{color}">{value}</div>
            <div class="metric-note">{note}</div>
            <div class="metric-accent" style="background:{color}"></div>
        </div>
        """, unsafe_allow_html=True)


# ---------------- ANALYTICS ----------------

st.markdown(
    '<div class="section-heading">Threat Intelligence Overview</div>'
    '<div class="section-caption">Severity distribution and recent incident activity</div>',
    unsafe_allow_html=True
)

chart_col, activity_col = st.columns([1, 1], gap="large")

with chart_col:
    st.markdown("""
    <div class="panel">
        <div class="panel-title">Incident Severity Distribution</div>
        <div class="panel-caption">Breakdown of recorded incident severity</div>
    </div>
    """, unsafe_allow_html=True)

    if not df.empty and "severity" in df.columns:
        severity_data = (
            df["severity"]
            .fillna("Unknown")
            .astype(str)
            .str.title()
            .value_counts()
            .reset_index()
        )

        severity_data.columns = ["Severity", "Count"]

        severity_colors = {
            "Critical": "#FB7185",
            "High": "#F97316",
            "Medium": "#FBBF24",
            "Low": "#4ADE80",
            "Unknown": "#64748B"
        }

        fig = px.pie(
            severity_data,
            names="Severity",
            values="Count",
            hole=0.70,
            color="Severity",
            color_discrete_map=severity_colors
        )

        fig.update_traces(
            textposition="outside",
            textinfo="percent",
            marker=dict(line=dict(color="#0B1728", width=3))
        )

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#DCEBFA", family="Inter"),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.15,
                xanchor="center",
                x=0.5
            ),
            margin=dict(t=15, b=35, l=15, r=15),
            height=340,
            showlegend=True
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Severity analytics will appear when incident data is available.")


with activity_col:
    st.markdown("""
    <div class="panel">
        <div class="panel-title">Recent Incident Activity</div>
        <div class="panel-caption">Latest records received by SENTINELX</div>
    </div>
    """, unsafe_allow_html=True)

    if not df.empty:
        display_columns = [
            column for column in
            ["title", "status", "severity", "created_at"]
            if column in df.columns
        ]

        if display_columns:
            recent_df = df[display_columns].head(8).copy()

            st.dataframe(
                recent_df,
                use_container_width=True,
                hide_index=True,
                height=340
            )
        else:
            st.info("No displayable incident fields found.")
    else:
        st.info("No incident records have been received yet.")


# ---------------- AI AGENT NETWORK ----------------

st.markdown("---")

st.markdown(
    '<div class="section-heading">Autonomous AI Agent Network</div>'
    '<div class="section-caption">Six specialized agents coordinate the defensive incident response workflow</div>',
    unsafe_allow_html=True
)

agents = [
    ("01", "Detection Agent", "Analyzes incoming security events and identifies suspicious activity.", "#35BFFF"),
    ("02", "Investigation Agent", "Connects evidence and builds incident investigation context.", "#A78BFA"),
    ("03", "Threat Intelligence Agent", "Enriches findings with available threat intelligence.", "#22D3EE"),
    ("04", "Risk Assessment Agent", "Evaluates severity, confidence and potential impact.", "#FBBF24"),
    ("05", "Audit Agent", "Maintains evidence records and accountability.", "#4ADE80"),
    ("06", "Response Agent", "Coordinates human-approved defensive response workflows.", "#FB923C")
]

agent_cols = st.columns(3)

for index, (number, name, description, color) in enumerate(agents):
    with agent_cols[index % 3]:
        st.markdown(f"""
        <div class="agent-card">
            <div class="agent-number" style="color:{color}">AGENT / {number}</div>
            <div class="agent-name">{name}</div>
            <div class="agent-description">{description}</div>
        </div>
        """, unsafe_allow_html=True)
        st.write("")


# ---------------- INCIDENT EXPLORER ----------------

st.markdown("---")

st.markdown(
    '<div class="section-heading">Incident Explorer</div>'
    '<div class="section-caption">Search, filter and inspect available incident records</div>',
    unsafe_allow_html=True
)

if not df.empty:
    search_col, severity_col, status_col = st.columns([2, 1, 1])

    with search_col:
        search_text = st.text_input(
            "Search incidents",
            placeholder="Search by title or incident details..."
        )

    with severity_col:
        if "severity" in df.columns:
            severity_options = ["All"] + sorted(
                df["severity"].fillna("Unknown").astype(str).unique().tolist()
            )
            selected_severity = st.selectbox(
                "Severity",
                severity_options
            )
        else:
            selected_severity = "All"

    with status_col:
        if "status" in df.columns:
            status_options = ["All"] + sorted(
                df["status"].fillna("Unknown").astype(str).unique().tolist()
            )
            selected_status = st.selectbox(
                "Status",
                status_options
            )
        else:
            selected_status = "All"

    filtered_df = df.copy()

    if selected_severity != "All" and "severity" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["severity"].fillna("Unknown").astype(str)
            == selected_severity
        ]

    if selected_status != "All" and "status" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["status"].fillna("Unknown").astype(str)
            == selected_status
        ]

    if search_text.strip():
        searchable_columns = [
            column for column in
            ["title", "description", "status", "severity"]
            if column in filtered_df.columns
        ]

        if searchable_columns:
            search_mask = filtered_df[searchable_columns].fillna("").astype(str).apply(
                lambda column: column.str.contains(
                    search_text,
                    case=False,
                    regex=False
                )
            ).any(axis=1)

            filtered_df = filtered_df[search_mask]

    st.caption(f"Showing {len(filtered_df)} of {len(df)} incidents")

    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        height=400
    )

else:
    st.info(
        "Your incident explorer is ready. "
        "No incident records are currently available."
    )


# ---------------- PLATFORM STATUS ----------------

st.markdown("---")

st.markdown("""
<div class="status-strip">
    <b style="color:#42C7FF;">SENTINELX PLATFORM PRINCIPLES</b><br><br>
    ◈ Evidence-backed analysis
    &nbsp;&nbsp; | &nbsp;&nbsp;
    ◈ Human oversight for consequential actions
    &nbsp;&nbsp; | &nbsp;&nbsp;
    ◈ Auditable incident records
</div>
""", unsafe_allow_html=True)


# ---------------- FOOTER ----------------

st.markdown("---")

st.markdown(f"""
<div class="footer">
    SENTINELX SECURITY OPERATIONS<br>
    DETECT. INVESTIGATE. VERIFY. RESPOND.<br><br>
    LAST DASHBOARD RENDER: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
</div>
""", unsafe_allow_html=True)


