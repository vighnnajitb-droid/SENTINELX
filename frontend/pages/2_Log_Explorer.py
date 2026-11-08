
import os
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")

st.set_page_config(
    page_title="SENTINELX | Log Explorer",
    page_icon="🔍",
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
.small-label {
    color: #91a8c4;
    font-size: 13px;
    letter-spacing: 1px;
}
div.stButton > button {
    background: #1677d2;
    color: white;
    border: 0;
    border-radius: 8px;
    min-height: 43px;
    font-weight: 600;
}
div.stButton > button:hover {
    background: #258ce9;
    color: white;
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
    <div class="small-label">SENTINELX / SECURITY OPERATIONS</div>
    <h1>🔍 Log Analysis Workspace</h1>
    <p>Ingest security telemetry, create incidents and initiate AI-powered investigations.</p>
</div>
""", unsafe_allow_html=True)

# Upload workspace
left, right = st.columns([1.5, 1])

with left:
    st.markdown("### 📂 Log Ingestion")
    st.markdown(
        '<div class="panel">Upload authorized security logs in CSV or JSON format.</div>',
        unsafe_allow_html=True
    )

    uploaded_file = st.file_uploader(
        "Drop your security log file here",
        type=["csv", "json"],
        help="Supported formats: CSV and JSON"
    )

    if uploaded_file:
        st.success(f"File selected: {uploaded_file.name}")

        st.caption(
            f"File size: {uploaded_file.size / 1024:.2f} KB"
        )

        if st.button("🚀 Upload & Analyze Logs", use_container_width=True):
            try:
                with st.spinner("Uploading and processing security events..."):
                    files = {
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            "application/octet-stream"
                        )
                    }

                    response = requests.post(
                        f"{API_URL}/logs/upload",
                        headers=headers,
                        files=files,
                        timeout=60
                    )

                if response.status_code == 200:
                    data = response.json()
                    incident_id = data.get("incident_id")

                    st.session_state["last_uploaded_incident"] = incident_id

                    st.success("Log ingestion completed successfully!")

                    metric1, metric2 = st.columns(2)

                    with metric1:
                        st.metric(
                            "Events Processed",
                            data.get("events_count", 0)
                        )

                    with metric2:
                        st.metric(
                            "Incident Created",
                            "Yes" if incident_id else "No"
                        )

                    if incident_id:
                        st.code(incident_id, language="text")

                        st.markdown("### 🧠 AI Investigation")

                        if st.button(
                            "Start AI Investigation",
                            key="start_investigation",
                            use_container_width=True
                        ):
                            try:
                                with st.spinner(
                                    "Starting investigation workflow..."
                                ):
                                    inv_response = requests.post(
                                        f"{API_URL}/investigations/{incident_id}/run",
                                        headers=headers,
                                        timeout=60
                                    )

                                if inv_response.status_code in (200, 201, 202):
                                    st.success(
                                        "Investigation request accepted!"
                                    )
                                    st.info(
                                        "Open Investigation Center or Agent Operations "
                                        "to inspect the results."
                                    )
                                else:
                                    st.error(
                                        f"Investigation failed: {inv_response.text}"
                                    )

                            except requests.RequestException as e:
                                st.error(f"Connection error: {e}")

                else:
                    st.error(
                        f"Upload failed ({response.status_code}): "
                        f"{response.text[:1000]}"
                    )

            except requests.RequestException as e:
                st.error(f"Could not connect to the backend: {e}")

with right:
    st.markdown("### 📡 Ingestion Pipeline")

    st.markdown("""
    <div class="panel">
        <p class="small-label">PIPELINE OVERVIEW</p>
        <h4>01 · Log Upload</h4>
        <p>Receive CSV or JSON security events.</p>
        <hr>
        <h4>02 · Event Processing</h4>
        <p>Backend validates and processes uploaded events.</p>
        <hr>
        <h4>03 · Incident Creation</h4>
        <p>Create an incident record from processed logs.</p>
        <hr>
        <h4>04 · AI Investigation</h4>
        <p>Trigger the SENTINELX investigation workflow.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🛡️ Supported Formats")
    st.info("CSV — Structured security event records")
    st.info("JSON — Structured or nested event data")

# Previous upload
last_incident = st.session_state.get("last_uploaded_incident")

if last_incident:
    st.markdown("### 🗂️ Latest Uploaded Incident")
    st.code(last_incident)

st.divider()

# Sample datasets
st.markdown("### 🧪 Sample Datasets")
st.write(
    "Use synthetic demonstration data from your project's "
    "`sample_data/` directory."
)

sample1, sample2, sample3 = st.columns(3)

with sample1:
    st.markdown("**Normal Activity**")
    st.caption("Baseline traffic for ordinary event analysis.")

with sample2:
    st.markdown("**Suspicious Activity**")
    st.caption("Synthetic security events for detection testing.")

with sample3:
    st.markdown("**Mixed Activity**")
    st.caption("A combination of normal and suspicious events.")

st.caption(
    "SENTINELX · Autonomous Incident Response Network · "
    "Use only authorized or synthetic security logs."
)
