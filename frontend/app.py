
import os
import textwrap
import requests
import streamlit as st

from dotenv import load_dotenv
from sentinelx_ui.theme import apply_theme

# ============================================================
# 1. CONFIGURATION
# ============================================================

load_dotenv(override=True)

API_URL = os.getenv(
    "API_URL",
    "http://127.0.0.1:8000/api/v1"
).rstrip("/")

st.set_page_config(
    page_title="SENTINELX | Security Operations",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apply existing application theme
apply_theme()


# ============================================================
# 2. HTML RENDERING
# ============================================================

def render_html(content):
    """
    Render HTML directly.
    Avoids Markdown interpreting indented HTML as code blocks.
    """
    st.html(textwrap.dedent(content).strip())


# ============================================================
# 3. CUSTOM LOGIN PAGE DESIGN
# ============================================================

render_html("""
<style>

/* ---------------- PAGE LAYOUT ---------------- */

.block-container {
    max-width: 1500px;
    padding: 2rem 3rem 2rem 3rem;
}

[data-testid="stAppViewContainer"] {
    background: #030b1b;
}

[data-testid="stHeader"] {
    background: transparent;
}

/* ---------------- BRAND ---------------- */

.brand {
    font-size: 38px;
    font-weight: 900;
    letter-spacing: -1.5px;
    color: #f5f8ff;
}

.brand span {
    color: #00d9ff;
}

.brand-sub {
    color: #819bb9;
    font-size: 10px;
    letter-spacing: 2.5px;
    margin-top: 7px;
}

/* ---------------- HERO ---------------- */

.hero {
    background: linear-gradient(
        140deg,
        #102f4b 0%,
        #091c32 55%,
        #071426 100%
    );
    border: 1px solid #087fc4;
    border-radius: 16px;
    padding: 32px;
    margin-bottom: 28px;
    min-height: 300px;
    box-shadow: 0 12px 35px rgba(0, 0, 0, 0.18);
}

.eyebrow {
    color: #00d9ff;
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 1.5px;
}

.hero-title {
    color: #f5f8ff;
    font-size: clamp(27px, 3vw, 43px);
    font-weight: 900;
    line-height: 1.25;
    letter-spacing: -1px;
    margin-top: 25px;
}

.hero-title span {
    color: #00d9ff;
}

.hero-desc {
    color: #a9bfd8;
    font-size: 14px;
    line-height: 1.9;
    margin-top: 20px;
    max-width: 650px;
}

/* ---------------- FEATURE SECTION ---------------- */

.section-label {
    color: #f0f6ff;
    font-size: 19px;
    font-weight: 800;
    margin: 28px 0 18px 0;
}

.feature-card {
    background: #101f34;
    border: 1px solid #16466d;
    border-radius: 12px;
    padding: 21px;
    min-height: 155px;
    margin-bottom: 15px;
    transition: border-color 0.2s ease;
}

.feature-card:hover {
    border-color: #00d9ff;
}

.feature-icon {
    color: #00d9ff;
    font-size: 24px;
    margin-bottom: 13px;
}

.feature-title {
    color: #f3f7ff;
    font-size: 13px;
    font-weight: 800;
    margin-bottom: 10px;
}

.feature-desc {
    color: #a7bdd7;
    font-size: 12px;
    line-height: 1.8;
}

/* ---------------- LOGIN PANEL ---------------- */

.login-panel {
    background: #0b1b30;
    border: 1px solid #16466d;
    border-radius: 15px 15px 0 0;
    padding: 30px;
}

.login-heading {
    color: #f5f8ff;
    font-size: 30px;
    font-weight: 800;
    margin-top: 16px;
}

.login-caption {
    color: #91aac8;
    font-size: 13px;
    line-height: 1.8;
    margin-top: 9px;
}

/* ---------------- LOGIN FORM ---------------- */

div[data-testid="stForm"] {
    background: #0b192c;
    border: 1px solid #16466d;
    border-radius: 0 0 15px 15px;
    padding: 25px;
}

div[data-testid="stTextInput"] label {
    color: #e5efff;
    font-size: 12px;
    font-weight: 700;
}

div[data-testid="stTextInput"] input {
    background: #111f34;
    border: 1px solid #285477;
    border-radius: 8px;
    color: #ffffff;
    min-height: 45px;
}

div[data-testid="stTextInput"] input:focus {
    border-color: #00cfff;
    box-shadow: 0 0 0 1px #00cfff;
}

div[data-testid="stFormSubmitButton"] button {
    min-height: 49px;
    border: 1px solid #008cff;
    border-radius: 8px;
    background: linear-gradient(
        110deg,
        #103b63,
        #0b2948
    );
    color: #ffffff;
    font-weight: 800;
    transition: all 0.2s ease;
}

div[data-testid="stFormSubmitButton"] button:hover {
    border-color: #00d9ff;
    background: #10416b;
    color: #ffffff;
}

/* ---------------- STATUS ---------------- */

.status-strip {
    background: #0b192c;
    border: 1px solid #16466d;
    border-radius: 12px;
    padding: 23px;
    margin-top: 22px;
    color: #d7e8fa;
    font-size: 13px;
    line-height: 1.8;
}

.status-dot {
    color: #00e69a;
    font-size: 15px;
}

/* ---------------- FOOTER ---------------- */

.footer {
    text-align: center;
    color: #718ba9;
    font-size: 10px;
    letter-spacing: 1.5px;
    padding: 35px 0 10px 0;
}

/* ---------------- RESPONSIVE ---------------- */

@media (max-width: 900px) {
    .block-container {
        padding: 1rem;
    }

    .hero {
        padding: 22px;
        min-height: auto;
    }

    .brand {
        font-size: 31px;
    }

    .login-panel {
        padding: 22px;
    }
}

</style>
""")


# ============================================================
# 4. SESSION STATE
# ============================================================

if "token" not in st.session_state:
    st.session_state["token"] = None


# ============================================================
# 5. AUTHENTICATION
# ============================================================

def login(username, password):

    try:
        login_url = f"{API_URL}/auth/login"

        response = requests.post(
            login_url,
            data={
                "username": username,
                "password": password
            },
            timeout=30
        )

        if response.status_code == 200:

            try:
                response_data = response.json()
            except ValueError:
                st.error("Backend returned an invalid response.")
                return

            token = response_data.get("access_token")

            if token:
                st.session_state["token"] = token
                st.session_state["username"] = username
                st.rerun()

            else:
                st.error("Authentication token was not returned.")
                st.write(
                    "Response fields:",
                    list(response_data.keys())
                )

        elif response.status_code in (400, 401):

            st.error("Login rejected by backend.")
            st.write("HTTP Status:", response.status_code)
            st.write("Request URL:", response.url)

        else:

            st.error(
                f"Login failed with HTTP {response.status_code}."
            )
            st.code(response.text[:500])

    except requests.Timeout:
        st.error("Backend request timed out.")

    except requests.ConnectionError:
        st.error("Cannot connect to the SENTINELX backend.")
        st.write("Configured API:", API_URL)

    except requests.RequestException as error:
        st.error("Authentication request failed.")
        st.code(type(error).__name__)


def logout():

    st.session_state["token"] = None
    st.session_state.pop("username", None)

    st.rerun()


# ============================================================
# 6. BRAND HEADER
# ============================================================

def brand_header():

    render_html("""
    <div style="padding: 5px 0 25px 0;">

        <div class="brand">
            SENTINEL<span>X</span>
        </div>

        <div class="brand-sub">
            AUTONOMOUS INCIDENT RESPONSE NETWORK
        </div>

    </div>
    """)


# ============================================================
# 7. LOGIN SCREEN
# ============================================================

if not st.session_state["token"]:

    left, right = st.columns(
        [1.15, 0.85],
        gap="large"
    )

    # --------------------------------------------------------
    # LEFT SIDE: BRAND AND FEATURES
    # --------------------------------------------------------

    with left:

        brand_header()

        render_html("""
        <div class="hero">

            <div class="eyebrow">
                NEXT-GENERATION SECURITY OPERATIONS
            </div>

            <div class="hero-title">
                SEE THE THREAT.<br>
                <span>UNDERSTAND IT.</span><br>
                RESPOND WITH CONFIDENCE.
            </div>

            <div class="hero-desc">
                An intelligent security operations platform that brings
                detection, investigation, threat intelligence, risk
                assessment, audit and response into one coordinated network.
            </div>

        </div>

        <div class="section-label">
            THE SENTINELX NETWORK
        </div>
        """)

        features = [
            (
                "◈",
                "INTELLIGENT DETECTION",
                "Analyze incoming security events and identify suspicious activity."
            ),
            (
                "⌕",
                "DEEP INVESTIGATION",
                "Connect event evidence and build investigation context."
            ),
            (
                "⬡",
                "RISK ASSESSMENT",
                "Evaluate severity and confidence using available findings."
            ),
            (
                "⛨",
                "AUDIT & RESPONSE",
                "Preserve accountability and support human-approved response."
            )
        ]

        feature_columns = st.columns(2, gap="medium")

        for index, (icon, title, description) in enumerate(features):

            with feature_columns[index % 2]:

                render_html(f"""
                <div class="feature-card">

                    <div class="feature-icon">
                        {icon}
                    </div>

                    <div class="feature-title">
                        {title}
                    </div>

                    <div class="feature-desc">
                        {description}
                    </div>

                </div>
                """)

    # --------------------------------------------------------
    # RIGHT SIDE: LOGIN
    # --------------------------------------------------------

    with right:

        # Align login panel with hero section
        st.markdown(
            "<div style='height:85px'></div>",
            unsafe_allow_html=True
        )

        render_html("""
        <div class="login-panel">

            <div class="eyebrow">
                SECURE ACCESS PORTAL
            </div>

            <div class="login-heading">
                Welcome Back
            </div>

            <div class="login-caption">
                Authenticate to access your security operations workspace.
            </div>

        </div>
        """)

        with st.form("login_form"):

            username = st.text_input(
                "OPERATOR ID",
                placeholder="Enter your username"
            )

            password = st.text_input(
                "ACCESS PASSWORD",
                placeholder="Enter your password",
                type="password"
            )

            submitted = st.form_submit_button(
                "ACCESS COMMAND CENTER →",
                use_container_width=True
            )

            if submitted:

                if not username.strip() or not password:

                    st.warning(
                        "Enter both your operator ID and password."
                    )

                else:

                    login(
                        username.strip(),
                        password
                    )

        render_html("""
        <div class="status-strip">

            <span class="status-dot">●</span>
            &nbsp; Secure authentication portal

            <br><br>

            <span style="color:#7895b3;">
                Access is restricted to authenticated operators.
            </span>

        </div>
        """)

        with st.expander("Connection diagnostics"):

            st.write("Configured API:", API_URL)

    # --------------------------------------------------------
    # FOOTER
    # --------------------------------------------------------

    render_html("""
    <div class="footer">
        SENTINELX SECURITY OPERATIONS &nbsp; · &nbsp;
        DETECT. INVESTIGATE. VERIFY. RESPOND.
    </div>
    """)


# ============================================================
# 8. AUTHENTICATED SESSION
# ============================================================

else:

    st.switch_page("pages/1_Command_Center.py")
