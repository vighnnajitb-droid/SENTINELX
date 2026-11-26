
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

/* PAGE LAYOUT */

.block-container {
    max-width: 1500px;
    padding: 2rem 3rem;
}

[data-testid="stAppViewContainer"] {
    background: #030b1b;
}

[data-testid="stHeader"] {
    background: transparent;
}

/* BRAND */

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

/* HERO */

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
    box-sizing: border-box;
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

/* FEATURE SECTION */

.section-label {
    color: #f0f6ff;
    font-size: 19px;
    font-weight: 800;
    margin: 28px 0 18px;
}

.feature-card {
    background: #101f34;
    border: 1px solid #16466d;
    border-radius: 12px;
    padding: 21px;
    min-height: 155px;
    height: 100%;
    margin-bottom: 15px;
    box-sizing: border-box;
    transition: border-color 0.2s ease,
                background 0.2s ease;
}

.feature-card:hover {
    border-color: #00d9ff;
    background: #12253c;
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

/* LOGIN PANEL */

.login-panel {
    background: #0b1b30;
    border: 1px solid #16466d;
    border-radius: 15px 15px 0 0;
    padding: 30px;
    box-sizing: border-box;
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

/* LOGIN FORM */

div[data-testid="stForm"] {
    background: #0b192c;
    border: 1px solid #16466d;
    border-top: none;
    border-radius: 0 0 15px 15px;
    padding: 25px;
    box-sizing: border-box;
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
    transition: border-color 0.2s ease,
                box-shadow 0.2s ease;
}

div[data-testid="stTextInput"] input:focus {
    border-color: #00cfff;
    box-shadow: 0 0 0 2px rgba(0, 207, 255, 0.14);
}

/* LOGIN BUTTON */

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
    transform: translateY(-1px);
}

div[data-testid="stFormSubmitButton"] button:active {
    transform: translateY(0);
}

/* STATUS */

.status-strip {
    background: #0b192c;
    border: 1px solid #16466d;
    border-radius: 12px;
    padding: 23px;
    margin-top: 22px;
    color: #d7e8fa;
    font-size: 13px;
    line-height: 1.8;
    box-sizing: border-box;
}

.status-dot {
    color: #00e69a;
    font-size: 15px;
}

/* EXPANDER */

div[data-testid="stExpander"] {
    border-color: #16466d;
    border-radius: 10px;
    margin-top: 12px;
}

/* FOOTER */

.footer {
    text-align: center;
    color: #718ba9;
    font-size: 10px;
    letter-spacing: 1.5px;
    padding: 35px 0 10px;
}

/* RESPONSIVE */

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

    .login-heading {
        font-size: 26px;
    }

    .feature-card {
        min-height: 145px;
    }

}

@media (max-width: 600px) {

    .block-container {
        padding: 0.8rem;
    }

    .hero {
        padding: 20px;
    }

    .hero-title {
        font-size: 28px;
    }

    .hero-desc {
        font-size: 13px;
    }

    .login-panel {
        padding: 20px;
    }

    div[data-testid="stForm"] {
        padding: 18px;
    }

    .footer {
        font-size: 9px;
        line-height: 1.8;
    }

}

</style>
""")


# ============================================================
# 4. SESSION STATE
# ============================================================

if "token" not in st.session_state:
    st.session_state["token"] = None

if "username" not in st.session_state:
    st.session_state["username"] = None


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

                st.error(
                    "Backend returned an invalid response."
                )
                return

            token = response_data.get("access_token")

            if token:

                st.session_state["token"] = token
                st.session_state["username"] = username

                st.rerun()

            else:

                st.error(
                    "Authentication token was not returned."
                )

                st.write(
                    "Response fields:",
                    list(response_data.keys())
                )

        elif response.status_code in (400, 401):

            st.error(
                "Login rejected by backend. Check your credentials."
            )

        elif response.status_code == 429:

            st.error(
                "Too many login requests. Please wait before trying again."
            )

            retry_after = response.headers.get("Retry-After")

            if retry_after:
                st.info(
                    f"Retry after: {retry_after} seconds."
                )

            st.caption(
                "If this happens on the first attempt, "
                "the backend rate-limit configuration needs investigation."
            )

        else:

            st.error(
                f"Login failed with HTTP {response.status_code}."
            )

            st.code(response.text[:500])

    except requests.Timeout:

        st.error(
            "Backend request timed out."
        )

    except requests.ConnectionError:

        st.error(
            "Cannot connect to the SENTINELX backend."
        )

        st.write(
            "Configured API:",
            API_URL
        )

    except requests.RequestException as error:

        st.error(
            "Authentication request failed."
        )

        st.code(
            type(error).__name__
        )


# ============================================================
# 6. LOGOUT
# ============================================================

def logout():

    st.session_state["token"] = None
    st.session_state["username"] = None

    st.rerun()


# ============================================================
# 7. BRAND HEADER
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
# 8. LOGIN SCREEN
# ============================================================

if not st.session_state["token"]:

    left, right = st.columns(
        [1.15, 0.85],
        gap="large"
    )

    # LEFT SIDE

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

        feature_columns = st.columns(
            2,
            gap="medium"
        )

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

    # RIGHT SIDE

    with right:

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
                placeholder="Enter your username",
                key="login_username"
            )

            password = st.text_input(
                "ACCESS PASSWORD",
                placeholder="Enter your password",
                type="password",
                key="login_password"
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

            st.write(
                "Configured API:",
                API_URL
            )

    # FOOTER

    render_html("""
    <div class="footer">
        SENTINELX SECURITY OPERATIONS &nbsp; · &nbsp;
        DETECT. INVESTIGATE. VERIFY. RESPOND.
    </div>
    """)


# ============================================================
# 9. AUTHENTICATED SESSION
# ============================================================

else:

    st.switch_page(
        "pages/1_Command_Center.py"
    )
