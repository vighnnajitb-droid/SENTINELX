
import os
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1")

st.set_page_config(
    page_title="SENTINELX | Security Operations",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- PREMIUM UI THEME --------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Orbitron:wght@500;600;700;800&display=swap');

.stApp {
    background:
        radial-gradient(ellipse at 10% 10%, rgba(0,120,255,.13), transparent 38%),
        radial-gradient(ellipse at 90% 85%, rgba(0,220,255,.08), transparent 35%),
        #070d18;
    color: #e8f1ff;
    font-family: 'Inter', sans-serif;
}

header[data-testid="stHeader"] {
    background: rgba(7,13,24,.75);
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1450px;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#0c1728,#07101d);
    border-right: 1px solid #1c3552;
}

[data-testid="stSidebar"] * {
    color: #d9e8fa;
}

h1, h2, h3 {
    color: #edf6ff !important;
}

p, label {
    color: #a9bbd2;
}

.brand {
    font-family: 'Orbitron', sans-serif;
    font-size: 34px;
    font-weight: 800;
    letter-spacing: 5px;
    color: #f1f8ff;
}

.brand span {
    color: #22baff;
}

.brand-sub {
    color: #7898b8;
    font-size: 11px;
    letter-spacing: 4px;
    margin-top: 5px;
}

.hero {
    position: relative;
    overflow: hidden;
    background: linear-gradient(115deg,rgba(15,35,61,.98),rgba(8,22,39,.96));
    border: 1px solid #234568;
    border-radius: 20px;
    padding: 42px;
    margin-bottom: 25px;
    box-shadow: 0 15px 55px rgba(0,0,0,.25);
}

.hero:after {
    content: " ";
    position: absolute;
    width: 300px;
    height: 300px;
    right: -90px;
    top: -120px;
    border-radius: 50%;
    border: 1px solid rgba(36,185,255,.2);
    box-shadow: 0 0 0 35px rgba(36,185,255,.025),
                0 0 0 70px rgba(36,185,255,.02);
}

.eyebrow {
    color: #38c5ff;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 3px;
    margin-bottom: 15px;
}

.hero-title {
    font-family: 'Orbitron', sans-serif;
    font-size: clamp(28px,4vw,48px);
    font-weight: 800;
    line-height: 1.2;
    color: #f2f8ff;
    margin-bottom: 15px;
}

.hero-title span {
    color: #26bfff;
}

.hero-desc {
    color: #a7bdd6;
    font-size: 15px;
    line-height: 1.8;
    max-width: 650px;
}

.section-label {
    color: #43bfff;
    font-size: 11px;
    letter-spacing: 3px;
    font-weight: 700;
    margin: 25px 0 12px 0;
}

.feature-card {
    background: linear-gradient(145deg,#101f33,#0c1727);
    border: 1px solid #203a58;
    border-radius: 14px;
    padding: 21px;
    min-height: 155px;
    transition: .2s ease;
}

.feature-icon {
    font-size: 25px;
    margin-bottom: 13px;
}

.feature-title {
    color: #e8f4ff;
    font-size: 15px;
    font-weight: 700;
    margin-bottom: 7px;
}

.feature-desc {
    color: #8fa9c5;
    font-size: 12px;
    line-height: 1.7;
}

.login-panel {
    background: linear-gradient(145deg,rgba(17,36,59,.98),rgba(9,20,35,.98));
    border: 1px solid #285477;
    border-radius: 19px;
    padding: 30px;
    box-shadow: 0 15px 50px rgba(0,0,0,.35);
}

.login-heading {
    color: #f1f7ff;
    font-family: 'Orbitron', sans-serif;
    font-size: 21px;
    font-weight: 700;
}

.login-caption {
    color: #8fa9c5;
    font-size: 12px;
    margin-top: 7px;
    margin-bottom: 20px;
}

.stTextInput input {
    background: #091525 !important;
    color: #e8f5ff !important;
    border: 1px solid #294765 !important;
    border-radius: 9px !important;
}

.stTextInput input:focus {
    border-color: #27baff !important;
    box-shadow: 0 0 0 1px #27baff !important;
}

div.stButton > button,
div.stFormSubmitButton > button {
    width: 100%;
    min-height: 46px;
    border-radius: 9px;
    border: 1px solid #25aef2;
    background: linear-gradient(100deg,#087bc5,#13a9e9);
    color: white;
    font-weight: 700;
    transition: .2s ease;
}

div.stButton > button:hover,
div.stFormSubmitButton > button:hover {
    background: linear-gradient(100deg,#139ce9,#26c4ff);
    border-color: #6bd8ff;
    color: white;
}

.status-strip {
    background: rgba(12,29,48,.9);
    border: 1px solid #1d3c5b;
    border-radius: 11px;
    padding: 15px 18px;
    color: #a9c0d8;
    font-size: 12px;
}

.status-dot {
    color: #36e5a2;
    font-size: 15px;
}

.footer {
    text-align: center;
    color: #58728e;
    font-size: 11px;
    letter-spacing: 1px;
    padding-top: 35px;
}

[data-testid="stMetric"] {
    background: #101f33;
    padding: 15px;
    border: 1px solid #203a58;
    border-radius: 12px;
}

hr {
    border-color: #20354e;
}
</style>
""", unsafe_allow_html=True)


# -------------------- AUTHENTICATION --------------------

if "token" not in st.session_state:
    st.session_state["token"] = None


def login(username, password):
    try:
        response = requests.post(
            f"{API_URL}/auth/login",
            data={
                "username": username,
                "password": password
            },
            timeout=20
        )

        if response.status_code == 200:
            token = response.json().get("access_token")

            if token:
                st.session_state["token"] = token
                st.rerun()
            else:
                st.error("Authentication response did not contain an access token.")

        elif response.status_code in (400, 401):
            st.error("Invalid username or password.")

        else:
            st.error(
                f"Login failed ({response.status_code}). "
                "Please check the backend service."
            )

    except requests.RequestException:
        st.error("Unable to connect to the backend. Please try again.")


def logout():
    st.session_state["token"] = None
    st.rerun()


# -------------------- BRAND HEADER --------------------

def brand_header():
    st.markdown("""
    <div style="padding:5px 0 22px 0;">
        <div class="brand">SENTINEL<span>X</span></div>
        <div class="brand-sub">AUTONOMOUS INCIDENT RESPONSE NETWORK</div>
    </div>
    """, unsafe_allow_html=True)


# -------------------- LOGIN SCREEN --------------------

if not st.session_state["token"]:

    left, right = st.columns([1.2, 0.85], gap="large")

    with left:
        brand_header()

        st.markdown("""
        <div class="hero">
            <div class="eyebrow">NEXT-GENERATION SECURITY OPERATIONS</div>
            <div class="hero-title">
                SEE THE THREAT.<br>
                <span>UNDERSTAND IT.</span><br>
                RESPOND WITH CONFIDENCE.
            </div>
            <div class="hero-desc">
                An intelligent security operations platform that brings
                detection, investigation, threat intelligence, risk assessment,
                audit and response into one coordinated network.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-label">THE SENTINELX NETWORK</div>',
                    unsafe_allow_html=True)

        features = [
            ("◈", "INTELLIGENT DETECTION",
             "Analyze incoming security events and identify suspicious activity."),
            ("⌕", "DEEP INVESTIGATION",
             "Connect event evidence and build investigation context."),
            ("⬡", "RISK ASSESSMENT",
             "Evaluate severity and confidence using available findings."),
            ("⛨", "AUDIT & RESPONSE",
             "Preserve accountability and support human-approved response.")
        ]

        cols = st.columns(2)

        for index, (icon, title, description) in enumerate(features):
            with cols[index % 2]:
                st.markdown(f"""
                <div class="feature-card">
                    <div class="feature-icon">{icon}</div>
                    <div class="feature-title">{title}</div>
                    <div class="feature-desc">{description}</div>
                </div>
                """, unsafe_allow_html=True)

    with right:
        st.markdown("<div style='height:85px'></div>", unsafe_allow_html=True)

        st.markdown("""
        <div class="login-panel">
            <div class="eyebrow">SECURE ACCESS PORTAL</div>
            <div class="login-heading">Welcome Back</div>
            <div class="login-caption">
                Authenticate to access your security operations workspace.
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input(
                "OPERATOR ID",
                placeholder="Enter your username"
            )

            password = st.text_input(
                "ACCESS PASSWORD",
                type="password",
                placeholder="Enter your password"
            )

            submitted = st.form_submit_button(
                "ACCESS COMMAND CENTER →",
                use_container_width=True
            )

            if submitted:
                if not username.strip() or not password:
                    st.warning("Enter both username and password.")
                else:
                    login(username.strip(), password)

        st.markdown("""
        <div class="status-strip">
            <span class="status-dot">●</span>
            &nbsp; Secure authentication portal<br><br>
            <span style="color:#7895b3;">
                Access is restricted to authenticated operators.
            </span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div class="footer">
        SENTINELX SECURITY OPERATIONS &nbsp; · &nbsp;
        DETECT. INVESTIGATE. VERIFY. RESPOND.
    </div>
    """, unsafe_allow_html=True)


# -------------------- AUTHENTICATED HOME --------------------

else:

    st.sidebar.markdown("""
    <div style="padding:12px 0 18px 0;">
        <div class="brand" style="font-size:24px;">SENTINEL<span>X</span></div>
        <div class="brand-sub" style="font-size:9px;letter-spacing:2px;">
            SECURITY OPERATIONS
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### OPERATOR WORKSPACE")
    st.sidebar.caption("Navigate through the security modules using the page menu.")

    if st.sidebar.button("↪ LOG OUT", use_container_width=True):
        logout()

    brand_header()

    st.markdown("""
    <div class="hero">
        <div class="eyebrow">SECURITY OPERATIONS / OVERVIEW</div>
        <div class="hero-title">
            COMMAND <span>CENTER</span>
        </div>
        <div class="hero-desc">
            Your centralized workspace for security event analysis,
            coordinated AI investigations, risk intelligence and
            accountable incident response.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-label">AVAILABLE SECURITY MODULES</div>',
                unsafe_allow_html=True)

    modules = [
        ("◈", "COMMAND CENTER", "Monitor incident records and security overview."),
        ("⌕", "LOG EXPLORER", "Upload and inspect security event data."),
        ("⬡", "INVESTIGATION CENTER", "Run and review incident investigations."),
        ("✳", "AGENT OPERATIONS", "Inspect individual AI agent findings."),
        ("⚑", "RISK ASSESSMENT", "Review severity and confidence assessments."),
        ("⛨", "AUDIT TRAIL", "Review recorded incident activity and evidence."),
        ("▤", "REPORTS", "Generate and export incident reports."),
        ("⚙", "SETTINGS", "Review available platform settings.")
    ]

    for start in range(0, len(modules), 4):
        cols = st.columns(4)

        for col, (icon, title, description) in zip(
            cols, modules[start:start + 4]
        ):
            with col:
                st.markdown(f"""
                <div class="feature-card">
                    <div class="feature-icon">{icon}</div>
                    <div class="feature-title">{title}</div>
                    <div class="feature-desc">{description}</div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown('<div class="section-label">PLATFORM PRINCIPLES</div>',
                unsafe_allow_html=True)

    st.markdown("""
    <div class="status-strip">
        <span class="status-dot">●</span>
        &nbsp; Evidence-backed analysis
        &nbsp;&nbsp; | &nbsp;&nbsp;
        Human oversight for consequential actions
        &nbsp;&nbsp; | &nbsp;&nbsp;
        Auditable incident records
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="footer">
        SENTINELX · AUTONOMOUS INCIDENT RESPONSE NETWORK<br>
        DETECT. INVESTIGATE. VERIFY. RESPOND.
    </div>
    """, unsafe_allow_html=True)
