
import os
import requests
import pandas as pd
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")

st.set_page_config(
    page_title="SENTINELX | Audit Intelligence",
    page_icon="📜",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background: #080f1c;
    color: #e5edf8;
}
.block-container {
    padding-top: 2rem;
    max-width: 1450px;
}
.hero {
    background: linear-gradient(120deg,#101f35,#142d49);
    padding: 25px;
    border: 1px solid #263e5d;
    border-radius: 14px;
    margin-bottom: 22px;
}
.hero h1 {
    color: #f1f6ff;
    margin-bottom: 5px;
}
.hero p {
    color: #9eb2ca;
    margin-bottom: 0;
}
.panel {
    background: #101b2b;
    border: 1px solid #243750;
    padding: 20px;
    border-radius: 12px;
    margin-bottom: 15px;
}
.metric-card {
    background: #101b2b;
    border: 1px solid #243750;
    border-radius: 11px;
    padding: 17px;
}
.metric-label {
    color: #91a8c4;
    font-size: 12px;
    letter-spacing: 1px;
}
.metric-value {
    color: #f1f6ff;
    font-size: 25px;
    font-weight: 700;
    margin-top: 5px;
}
.small-label {
    color: #91a8c4;
    font-size: 12px;
    letter-spacing: 1px;
}
</style>
""", unsafe_allow_html=True)

if "token" not in st.session_state or not st.session_state["token"]:
    st.warning("Please log in from the main page.")
    st.stop()

headers = {
    "Authorization": f"Bearer {st.session_state['token']}"
}

st.markdown("""
<div class="hero">
    <div class="small-label">SENTINELX / EVIDENCE & ACCOUNTABILITY</div>
    <h1>📜 Audit Intelligence Console</h1>
    <p>Review incident activity, system actions and available evidence integrity records.</p>
</div>
""", unsafe_allow_html=True)

# Fetch incidents
try:
    with st.spinner("Loading incident records..."):
        inc_resp = requests.get(
            f"{API_URL}/incidents",
            headers=headers,
            timeout=20
        )

    if inc_resp.status_code != 200:
        st.error(
            f"Incident request failed ({inc_resp.status_code}): "
            f"{inc_resp.text[:500]}"
        )
        st.stop()

    incidents = inc_resp.json()

    if not isinstance(incidents, list):
        st.error("Unexpected incident data received.")
        st.stop()

except requests.RequestException as e:
    st.error(f"Backend connection failed: {e}")
    st.stop()

if not incidents:
    st.info("No incidents available for audit review.")
    st.stop()

incident_options = {
    f"{item.get('title', 'Untitled Incident')} "
    f"({str(item.get('id', ''))[:8]})": item.get("id")
    for item in incidents
    if item.get("id")
}

if not incident_options:
    st.warning("No valid incident identifiers found.")
    st.stop()

st.markdown("### 🎯 Select Incident")

selected_inc = st.selectbox(
    "Choose an incident to audit",
    options=list(incident_options.keys())
)

incident_id = incident_options[selected_inc]

# Fetch audit records
try:
    with st.spinner("Retrieving audit records..."):
        audit_resp = requests.get(
            f"{API_URL}/incidents/{incident_id}/audit",
            headers=headers,
            timeout=30
        )

    if audit_resp.status_code != 200:
        st.error(
            f"Audit request failed ({audit_resp.status_code}): "
            f"{audit_resp.text[:500]}"
        )
        st.stop()

    logs = audit_resp.json()

    if not isinstance(logs, list):
        st.error("Unexpected audit data format received.")
        st.stop()

except requests.RequestException as e:
    st.error(f"Audit retrieval failed: {e}")
    st.stop()

st.divider()

# Summary metrics
st.markdown("### 📊 Audit Overview")

total_logs = len(logs)

entity_types = {
    str(log.get("entity_type", "Unknown"))
    for log in logs
}

actions = {
    str(log.get("action", "Unknown"))
    for log in logs
}

m1, m2, m3 = st.columns(3)

with m1:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">'
        f'TOTAL AUDIT RECORDS</div><div class="metric-value">'
        f'{total_logs}</div></div>',
        unsafe_allow_html=True
    )

with m2:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">'
        f'ENTITY TYPES</div><div class="metric-value">'
        f'{len(entity_types)}</div></div>',
        unsafe_allow_html=True
    )

with m3:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">'
        f'UNIQUE ACTIONS</div><div class="metric-value">'
        f'{len(actions)}</div></div>',
        unsafe_allow_html=True
    )

if not logs:
    st.info("No audit logs found for this incident.")
    st.stop()

# Data preparation
df = pd.DataFrame(logs)

st.divider()
st.markdown("### 🔎 Audit Record Explorer")

# Search and filter
search_col, entity_col, action_col = st.columns(3)

with search_col:
    search_text = st.text_input(
        "Search audit records",
        placeholder="Search action, entity or hash..."
    )

with entity_col:
    entity_values = sorted(
        df["entity_type"].dropna().astype(str).unique().tolist()
    ) if "entity_type" in df.columns else []

    selected_entity = st.selectbox(
        "Filter by entity",
        ["All"] + entity_values
    )

with action_col:
    action_values = sorted(
        df["action"].dropna().astype(str).unique().tolist()
    ) if "action" in df.columns else []

    selected_action = st.selectbox(
        "Filter by action",
        ["All"] + action_values
    )

filtered_df = df.copy()

if selected_entity != "All" and "entity_type" in filtered_df.columns:
    filtered_df = filtered_df[
        filtered_df["entity_type"].astype(str) == selected_entity
    ]

if selected_action != "All" and "action" in filtered_df.columns:
    filtered_df = filtered_df[
        filtered_df["action"].astype(str) == selected_action
    ]

if search_text:
    search_mask = filtered_df.astype(str).apply(
        lambda column: column.str.contains(
            search_text,
            case=False,
            na=False,
            regex=False
        )
    ).any(axis=1)

    filtered_df = filtered_df[search_mask]

st.caption(
    f"Showing {len(filtered_df)} of {total_logs} audit records"
)

preferred_columns = [
    "timestamp",
    "entity_type",
    "action",
    "current_hash"
]

visible_columns = [
    column for column in preferred_columns
    if column in filtered_df.columns
]

if visible_columns:
    st.dataframe(
        filtered_df[visible_columns],
        use_container_width=True,
        hide_index=True
    )
else:
    st.warning("Expected audit summary fields are unavailable.")
    st.dataframe(filtered_df, use_container_width=True)

# Detailed record viewer
st.divider()
st.markdown("### 🧾 Detailed Audit Record")

if not filtered_df.empty:
    record_indices = filtered_df.index.tolist()

    selected_index = st.selectbox(
        "Select an audit record",
        options=record_indices,
        format_func=lambda index: (
            f"{df.loc[index].get('timestamp', 'Unknown time')} | "
            f"{df.loc[index].get('action', 'Unknown action')}"
        )
    )

    selected_record = df.loc[selected_index].to_dict()

    detail_left, detail_right = st.columns([1, 1])

    with detail_left:
        st.markdown("#### Record Information")

        for field in ["timestamp", "entity_type", "action"]:
            if field in selected_record:
                st.markdown(f"**{field.replace('_', ' ').title()}**")
                st.write(selected_record[field])

    with detail_right:
        st.markdown("#### Evidence Integrity")

        hash_fields = [
            key for key in selected_record
            if "hash" in key.lower()
        ]

        if hash_fields:
            for field in hash_fields:
                st.caption(field.replace("_", " ").title())
                st.code(str(selected_record[field]))
        else:
            st.info("No hash fields are available in this record.")

    with st.expander("View complete raw audit record"):
        st.json(selected_record)

else:
    st.info("No records match the selected filters.")

st.divider()

st.markdown("### 🛡️ Audit Integrity Notes")
st.info(
    "This console displays audit records returned by the backend. "
    "The presence of a hash is not, by itself, proof that the audit chain "
    "has been independently verified."
)

st.caption(
    "SENTINELX · Evidence & Accountability · "
    "Tamper-evident audit visibility"
)
