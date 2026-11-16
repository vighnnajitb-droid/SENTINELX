
import os
import requests
import streamlit as st
import json

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")

st.set_page_config(
    page_title="SENTINELX | Agent Operations",
    page_icon="🤖",
    layout="wide"
)

st.markdown("""
<style>
.stApp { background: #080E1B; color: #E6EDF7; }
h1, h2, h3 { color: #E6EDF7 !important; }
.agent-card {
    background: linear-gradient(135deg, #111C30, #142640);
    border: 1px solid #29415E;
    border-radius: 12px;
    padding: 17px;
    min-height: 115px;
}
.agent-title { color: #E6EDF7; font-weight: 700; }
.agent-desc { color: #91A6C1; font-size: 12px; margin-top: 7px; }
.console-header {
    background: linear-gradient(110deg, #10213A, #12334A);
    border: 1px solid #294D69;
    border-radius: 13px;
    padding: 22px;
}
</style>
""", unsafe_allow_html=True)

# Authentication
if not st.session_state.get("token"):
    st.warning("Please log in from the main page.")
    st.stop()

headers = {
    "Authorization": f"Bearer {st.session_state['token']}"
}

# Header
st.markdown("""
<div class="console-header">
    <h1>🤖 AI AGENT OPERATIONS</h1>
    <p style="color:#A5BCD5">
        SENTINELX | Autonomous Incident Response Network
    </p>
    <p style="color:#7DD3FC">
        Monitor agent results • Inspect execution data • Review investigations
    </p>
</div>
""", unsafe_allow_html=True)

st.write("")

if st.button("↻ Refresh Operations"):
    st.rerun()

# Agent architecture
st.subheader("Agent Network Architecture")

agents = [
    ("01", "Detection Agent", "Security event identification"),
    ("02", "Investigation Agent", "Incident investigation"),
    ("03", "Threat Intelligence Agent", "Threat context analysis"),
    ("04", "Risk Assessment Agent", "Risk and severity evaluation"),
    ("05", "Audit Agent", "Evidence and audit verification"),
    ("06", "Response Agent", "Human-approved response")
]

cols = st.columns(3)

for i, (number, name, description) in enumerate(agents):
    with cols[i % 3]:
        st.markdown(f"""
        <div class="agent-card">
            <div class="agent-title">{number} | {name}</div>
            <div class="agent-desc">{description}</div>
        </div>
        """, unsafe_allow_html=True)
        st.write("")

st.markdown("---")

# Fetch incidents
st.subheader("Investigation Workspace")

try:
    inc_resp = requests.get(
        f"{API_URL}/incidents",
        headers=headers,
        timeout=15
    )

    if inc_resp.status_code != 200:
        st.error(f"Incident API returned HTTP {inc_resp.status_code}")
        st.stop()

    incidents = inc_resp.json()

except requests.RequestException as error:
    st.error(f"Backend connection failed: {error}")
    st.stop()

except ValueError:
    st.error("The backend returned an invalid response.")
    st.stop()

if not incidents:
    st.info("No incidents are currently available for investigation.")
    st.stop()

incident_options = {
    f"{inc.get('title', 'Untitled Incident')} ({str(inc.get('id', ''))[:8]})":
    inc.get("id")
    for inc in incidents
    if inc.get("id")
}

if not incident_options:
    st.warning("No valid incident IDs were returned by the API.")
    st.stop()

selected_incident = st.selectbox(
    "Select an incident",
    list(incident_options.keys())
)

incident_id = incident_options[selected_incident]

# Fetch report
st.markdown("### Investigation Results")

try:
    report_response = requests.get(
        f"{API_URL}/reports/{incident_id}",
        headers=headers,
        timeout=20
    )

    if report_response.status_code == 200:
        report = report_response.json()

        investigations = report.get("investigations", [])

        if not investigations:
            st.info(
                "No investigation results are available for this incident yet."
            )
            st.stop()

        latest = investigations[-1]

        st.write(
            f"**Investigation status:** "
            f"`{latest.get('status', 'Unknown')}`"
        )

        agents_data = latest.get("agents", {})

        if not agents_data:
            st.warning("Agent outputs are not available yet.")
            st.stop()

        st.markdown("---")
        st.markdown("### Agent Execution Results")

        available_agents = list(agents_data.keys())

        selected_agent = st.selectbox(
            "Inspect individual agent",
            available_agents
        )

        output = agents_data[selected_agent]

        st.markdown(f"#### {selected_agent}")

        if isinstance(output, dict):
            result = output.get("status", "Result available")
            st.info(f"Result status: {result}")

            if "output" in output:
                st.markdown("**Agent Output**")
                st.write(output["output"])

            with st.expander("Inspect complete agent data"):
                st.json(output)

        elif isinstance(output, list):
            st.write(output)
            with st.expander("Inspect raw JSON"):
                st.json(output)

        else:
            st.write(output)

            with st.expander("Inspect raw JSON"):
                st.code(
                    json.dumps(output, indent=2, default=str),
                    language="json"
                )

        st.markdown("---")
        st.markdown("### Complete Investigation Data")

        with st.expander("View all agent results"):
            st.json(agents_data)

    elif report_response.status_code == 404:
        st.info("No report has been generated for this incident yet.")

    else:
        st.error(
            f"Report API returned HTTP {report_response.status_code}"
        )

except requests.RequestException as error:
    st.error(f"Could not retrieve investigation report: {error}")

except ValueError:
    st.error("The report API returned invalid JSON.")

st.markdown("---")
st.caption(
    "SENTINELX | Agent Operations Console | "
    "Agent execution states are based on returned backend results."
)
