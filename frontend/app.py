import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")

st.set_page_config(
    page_title="SENTINELX SOC",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark navy theme
st.markdown("""
    <style>
    .stApp {
        background-color: #0A1128;
        color: #E2E8F0;
    }
    .stSidebar {
        background-color: #050A19 !important;
    }
    h1, h2, h3, h4 {
        color: #60A5FA !important;
    }
    .stButton>button {
        background-color: #1E3A8A;
        color: white;
        border: 1px solid #3B82F6;
    }
    .stButton>button:hover {
        background-color: #3B82F6;
        border: 1px solid #60A5FA;
    }
    .metric-card {
        background-color: #111827;
        border: 1px solid #1F2937;
        border-radius: 8px;
        padding: 20px;
        text-align: center;
    }
    .metric-value {
        font-size: 2em;
        font-weight: bold;
        color: #60A5FA;
    }
    </style>
""", unsafe_allow_html=True)

# Authentication state
if 'token' not in st.session_state:
    st.session_state['token'] = None

def login(username, password):
    try:
        response = requests.post(f"{API_URL}/auth/login", data={"username": username, "password": password})
        if response.status_code == 200:
            st.session_state['token'] = response.json().get("access_token")
            st.rerun()
        else:
            st.error("Invalid credentials")
    except Exception as e:
        st.error(f"Connection error: {e}")

def logout():
    st.session_state['token'] = None
    st.rerun()

# Authentication UI
if not st.session_state['token']:
    st.title("SENTINELX Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            login(username, password)
else:
    st.sidebar.title("🛡️ SENTINELX")
    st.sidebar.markdown("*Detect. Investigate. Verify. Respond.*")
    if st.sidebar.button("Logout"):
        logout()
        
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Navigation")
    
    # Navigation is handled natively by Streamlit's pages functionality
    st.sidebar.info("Select a page from the menu above to navigate.")
    
    st.title("Welcome to SENTINELX Command Center")
    st.markdown("""
    **SENTINELX** is an autonomous incident response network.
    
    Use the navigation menu to access:
    - **Command Center:** Overview of system status and metrics.
    - **Log Explorer:** Upload and view raw security logs.
    - **Investigation Center:** Manage and view active investigations.
    - **Agent Operations:** Drill down into specific AI agent logic.
    - **Risk Assessment:** View severity and confidence scores.
    - **Audit Trail:** Review tamper-evident logs.
    - **Reports:** Generate and view incident reports.
    """)
    
    st.image("https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&q=80&w=800", caption="Cybersecurity Operations", width="stretch")