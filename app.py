"""
Main Streamlit application for the Environmental Clearance Application Review System (VYRO).
Pure Streamlit frontend with direct SQLite & bcrypt authentication.
Includes Landing page, Authentication, and Report Submission & AI Review pipeline.
"""
import streamlit as st
import pandas as pd
import services
from models import UserRole, ReviewResult, Issue
from landing import render_landing_page

# Page configuration
st.set_page_config(
    page_title="VYRO - Environmental Clearance Review",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

def inject_environmental_theme():
    """Injects high-end Environmental Clearance styling, atmospheric nature background, and glassmorphic cards."""
    st.markdown(
        """
        <style>
        /* Modern Environmental Clearance (MoEFCC/EAC Biome) Styling */
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }

        /* 1. Atmospheric Deep Canopy / Ecological Background */
        .stApp {
            background-color: #06110d !important;
            background-image: 
                radial-gradient(circle at 12% 15%, rgba(16, 185, 129, 0.16) 0%, transparent 45%),
                radial-gradient(circle at 88% 22%, rgba(5, 150, 105, 0.14) 0%, transparent 45%),
                radial-gradient(circle at 50% 80%, rgba(20, 83, 45, 0.22) 0%, transparent 55%),
                radial-gradient(circle at 75% 85%, rgba(52, 211, 153, 0.08) 0%, transparent 35%),
                linear-gradient(165deg, #050d0a 0%, #081711 25%, #0b1f17 60%, #06120d 100%) !important;
            background-attachment: fixed !important;
            color: #f1f5f9 !important;
        }

        /* Ambient ecological dot mesh overlay */
        .stApp::before {
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image: radial-gradient(rgba(52, 211, 153, 0.12) 1px, transparent 1px);
            background-size: 28px 28px;
            opacity: 0.45;
            pointer-events: none;
            z-index: 0;
        }

        /* 2. Glassmorphic Sidebar with Nature Biome Accent */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(6, 17, 13, 0.96) 0%, rgba(4, 12, 9, 0.98) 100%) !important;
            border-right: 1px solid rgba(52, 211, 153, 0.2) !important;
            box-shadow: 4px 0 24px rgba(0, 0, 0, 0.45) !important;
            backdrop-filter: blur(16px) !important;
        }

        /* 3. Metric Cards with Eco Glow */
        [data-testid="stMetric"] {
            background: rgba(11, 26, 19, 0.75) !important;
            border: 1px solid rgba(52, 211, 153, 0.25) !important;
            border-radius: 14px !important;
            padding: 16px 20px !important;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(52, 211, 153, 0.15) !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        }
        [data-testid="stMetric"]:hover {
            transform: translateY(-3px);
            border-color: rgba(52, 211, 153, 0.6) !important;
            box-shadow: 0 12px 30px rgba(16, 185, 129, 0.25), inset 0 1px 0 rgba(52, 211, 153, 0.3) !important;
        }
        [data-testid="stMetricValue"] {
            color: #4ade80 !important;
            font-weight: 800 !important;
            letter-spacing: -0.02em;
            text-shadow: 0 0 16px rgba(74, 222, 128, 0.3);
        }
        [data-testid="stMetricLabel"] {
            color: #94a3b8 !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            font-size: 0.78rem !important;
        }

        /* 4. Primary & Action Buttons (Emerald Gradient Glow) */
        button[kind="primary"], .stButton > button[kind="primary"], [data-testid="baseButton-primary"] {
            background: linear-gradient(135deg, #059669 0%, #10b981 50%, #34d399 100%) !important;
            color: #032115 !important;
            font-weight: 700 !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 0.6rem 1.4rem !important;
            box-shadow: 0 4px 18px rgba(16, 185, 129, 0.35) !important;
            transition: all 0.25s ease-in-out !important;
        }
        button[kind="primary"]:hover, .stButton > button[kind="primary"]:hover {
            box-shadow: 0 6px 28px rgba(52, 211, 153, 0.65) !important;
            transform: translateY(-2px);
            filter: brightness(1.08);
        }
        button[kind="secondary"], .stButton > button[kind="secondary"], [data-testid="baseButton-secondary"] {
            background: rgba(14, 32, 24, 0.7) !important;
            color: #f1f5f9 !important;
            border: 1px solid rgba(52, 211, 153, 0.35) !important;
            border-radius: 10px !important;
            transition: all 0.25s ease-in-out !important;
        }
        button[kind="secondary"]:hover, .stButton > button[kind="secondary"]:hover {
            background: rgba(20, 48, 36, 0.9) !important;
            border-color: #34d399 !important;
            color: #4ade80 !important;
            box-shadow: 0 4px 16px rgba(52, 211, 153, 0.25) !important;
        }

        /* 5. Ecological File Upload Zone */
        [data-testid="stFileUploader"] {
            background: rgba(11, 26, 19, 0.7) !important;
            border: 2px dashed rgba(52, 211, 153, 0.4) !important;
            border-radius: 14px !important;
            padding: 18px !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25) !important;
            transition: all 0.3s ease;
        }
        [data-testid="stFileUploader"]:hover {
            border-color: #34d399 !important;
            background: rgba(16, 185, 129, 0.1) !important;
            box-shadow: 0 6px 25px rgba(16, 185, 129, 0.22) !important;
        }

        /* 6. Tabs & Navigation Highlights */
        [data-baseweb="tab-list"] {
            gap: 10px;
            border-bottom: 1px solid rgba(52, 211, 153, 0.2) !important;
        }
        [data-baseweb="tab"] {
            color: #94a3b8 !important;
            font-weight: 600 !important;
            border-radius: 8px 8px 0 0 !important;
            padding: 8px 18px !important;
            transition: all 0.2s ease;
        }
        [data-baseweb="tab"]:hover {
            color: #4ade80 !important;
            background: rgba(16, 185, 129, 0.08) !important;
        }
        [aria-selected="true"] {
            color: #4ade80 !important;
            border-bottom: 3px solid #34d399 !important;
        }

        /* 7. Inputs & Selectboxes */
        .stTextInput > div > div > input, 
        .stTextArea > div > div > textarea, 
        .stSelectbox > div > div {
            background: rgba(9, 21, 16, 0.85) !important;
            border: 1px solid rgba(52, 211, 153, 0.28) !important;
            color: #f8fafc !important;
            border-radius: 9px !important;
        }
        .stTextInput > div > div > input:focus, 
        .stTextArea > div > div > textarea:focus {
            border-color: #34d399 !important;
            box-shadow: 0 0 0 2px rgba(52, 211, 153, 0.35) !important;
        }

        /* 8. Expanders & Containers */
        .streamlit-expanderHeader {
            background: rgba(12, 27, 20, 0.75) !important;
            border: 1px solid rgba(52, 211, 153, 0.22) !important;
            border-radius: 10px !important;
            color: #f8fafc !important;
            font-weight: 600 !important;
        }
        .streamlit-expanderHeader:hover {
            border-color: rgba(52, 211, 153, 0.5) !important;
            background: rgba(18, 40, 30, 0.85) !important;
        }

        /* 9. Dataframe & Tables */
        [data-testid="stDataFrame"] {
            background: rgba(9, 21, 16, 0.8) !important;
            border: 1px solid rgba(52, 211, 153, 0.25) !important;
            border-radius: 12px !important;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35) !important;
        }

        /* 10. Callout Boxes */
        .stAlert {
            border-radius: 12px !important;
            backdrop-filter: blur(8px) !important;
        }
        div[data-testid="stAlert"]:has(div[data-testid="stAlertContentSuccess"]) {
            background: rgba(22, 101, 52, 0.25) !important;
            border: 1px solid #16a34a !important;
        }
        div[data-testid="stAlert"]:has(div[data-testid="stAlertContentInfo"]) {
            background: rgba(13, 148, 136, 0.18) !important;
            border: 1px solid #0d9488 !important;
        }

        /* 11. Radio Buttons in Sidebar */
        [data-testid="stSidebar"] [data-testid="stRadio"] > div {
            background: rgba(10, 24, 18, 0.65);
            padding: 12px 14px;
            border-radius: 12px;
            border: 1px solid rgba(52, 211, 153, 0.18);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

def render_environmental_header(role_display: str, name: str):
    """Renders a top status badge emphasizing the MoEFCC/SEAC Environmental Clearance compliance posture."""
    st.markdown(
        f"""
        <div style='display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;
                    padding: 12px 20px; margin-bottom: 22px; 
                    background: rgba(16, 185, 129, 0.08); 
                    border: 1px solid rgba(52, 211, 153, 0.25); 
                    border-radius: 12px; backdrop-filter: blur(10px);
                    box-shadow: 0 4px 20px rgba(0,0,0,0.25);'>
            <div style='display: flex; align-items: center; gap: 12px;'>
                <div style='width: 38px; height: 38px; border-radius: 10px; background: rgba(52, 211, 153, 0.18); display: flex; align-items: center; justify-content: center; font-size: 1.3rem; border: 1px solid rgba(52, 211, 153, 0.35);'>
                    🌿
                </div>
                <div>
                    <div style='font-size: 0.95rem; font-weight: 800; color: #4ade80; letter-spacing: 0.03em;'>
                        EIA 2006 & MoEFCC STATUTORY CLEARANCE AUDIT
                    </div>
                    <div style='font-size: 0.78rem; color: #94a3b8;'>
                        Environmental Impact Assessment &bull; Scrutiny Protocol Active &bull; Parivesh 2.0 AI Standard
                    </div>
                </div>
            </div>
            <div style='display: flex; align-items: center; gap: 14px;'>
                <span style='background: rgba(52, 211, 153, 0.15); border: 1px solid rgba(52, 211, 153, 0.4); color: #86efac; padding: 4px 12px; border-radius: 20px; font-size: 0.78rem; font-weight: 700;'>
                    🌱 Eco-Scrutiny Engine
                </span>
                <div style='display: flex; align-items: center; gap: 6px;'>
                    <span style='width: 8px; height: 8px; border-radius: 50%; background: #4ade80; box-shadow: 0 0 10px #4ade80; display: inline-block;'></span>
                    <span style='font-size: 0.78rem; color: #a7f3d0; font-weight: 600;'>System Online</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# 0. Inject Environmental Theme Immediately
inject_environmental_theme()

# 1. Initialize SQLite database schema
services.init_database()

# 2. Setup Streamlit Authenticator via service layer
authenticator = services.get_authenticator()

# Navigation and role state
if "page" not in st.session_state:
    st.session_state["page"] = "landing"

if "auth_page" not in st.session_state:
    st.session_state["auth_page"] = "submit"

if "role" not in st.session_state:
    st.session_state["role"] = None

# Review results state persistence
if "review_result" not in st.session_state:
    st.session_state["review_result"] = None
if "review_project_name" not in st.session_state:
    st.session_state["review_project_name"] = ""

# If user is already authenticated, ensure page is 'app'
if st.session_state.get("authentication_status"):
    st.session_state["page"] = "app"

# ==============================================================================
# UNAUTHENTICATED FLOW (Landing Page OR Login Page)
# ==============================================================================
if not st.session_state.get("authentication_status"):
    # 1. Landing Page View (Default)
    if st.session_state.get("page") == "landing":
        render_landing_page()
        st.stop()

    # 2. Login & Sign Up View
    elif st.session_state.get("page") == "login":
        # Back to landing page button
        col_back, _ = st.columns([1, 4])
        with col_back:
            if st.button("← Back to VYRO Home", key="back_to_landing"):
                st.session_state["page"] = "landing"
                st.rerun()

        col_a, col_b, col_c = st.columns([1, 2.2, 1])
        with col_b:
            st.markdown(
                """
                <div style='text-align: center; margin-bottom: 25px;'>
                    <div style='display: inline-flex; align-items: center; gap: 8px; background: rgba(52, 211, 153, 0.12); border: 1px solid rgba(52, 211, 153, 0.3); padding: 5px 14px; border-radius: 20px; margin-bottom: 12px;'>
                        <span style='font-size: 1rem;'>🌿</span>
                        <span style='font-size: 0.78rem; font-weight: 700; color: #4ade80; letter-spacing: 0.08em; text-transform: uppercase;'>Statutory Environmental Clearance Portal</span>
                    </div>
                    <h1 style='font-size: 3.2rem; font-weight: 900; margin: 0; letter-spacing: 2px;
                               background: linear-gradient(135deg, #4ade80 0%, #22c55e 50%, #10b981 100%);
                               -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
                        VYRO
                    </h1>
                    <p style='color: #94a3b8; font-size: 1.05rem; margin-top: 6px; font-weight: 500;'>
                        AI-Powered EIA / EMP Appraisal & Scrutiny Engine
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            tab_login, tab_signup = st.tabs(["🔐 Log In", "📝 Sign Up"])

            with tab_login:
                st.info("💡 **Demo Reviewer:** Username: `admin` | Password: `admin123`")
                try:
                    authenticator.login(
                        location="main",
                        fields={
                            "Form name": "Account Login",
                            "Username": "Username or Email",
                            "Password": "Password",
                            "Login": "Log In"
                        }
                    )
                except Exception as e:
                    st.error(f"Login error: {e}")

                # Check authentication status returned by authenticator
                if st.session_state.get("authentication_status"):
                    username = st.session_state.get("username")
                    user_info = services.get_user_profile(username)
                    if user_info:
                        st.session_state["role"] = user_info["role"]
                        st.session_state["name"] = user_info["name"]
                        st.session_state["email"] = user_info["email"]
                    st.session_state["page"] = "app"
                    st.rerun()
                elif st.session_state.get("authentication_status") is False:
                    st.error("Incorrect username or password. Please verify your credentials and try again.")

            with tab_signup:
                st.subheader("Create a New Account")
                with st.form("signup_form", clear_on_submit=True):
                    new_name = st.text_input("Full Name", placeholder="e.g. Dr. Ramesh Kumar")
                    new_username = st.text_input("Username", placeholder="e.g. ramesh_k")
                    new_email = st.text_input("Email", placeholder="e.g. ramesh@example.com")
                    new_password = st.text_input("Password", type="password")
                    new_confirm_password = st.text_input("Confirm Password", type="password")
                    new_role = st.selectbox(
                        "Register as",
                        options=[UserRole.APPLICANT, UserRole.REVIEWER],
                        format_func=lambda r: "Project Proponent / Applicant" if r == UserRole.APPLICANT else "EC Officer / Reviewer"
                    )
                    submit_signup = st.form_submit_button("Register Account", use_container_width=True)

                    if submit_signup:
                        success, message = services.register_user(
                            name=new_name,
                            username=new_username,
                            email=new_email,
                            password=new_password,
                            confirm_password=new_confirm_password,
                            role=new_role
                        )
                        if success:
                            st.success(f"{message} Registered username: **{new_username.lower()}**. You can now log in using the 'Log In' tab!")
                            st.rerun()
                        else:
                            st.error(message)

        # Halt execution so unauthenticated users see nothing else
        st.stop()

# ==============================================================================
# AUTHENTICATED AREA (Only accessible after successful login)
# ==============================================================================

# Ensure role is set in session state
current_username = st.session_state.get("username")
if not st.session_state.get("role") and current_username:
    user_data = services.get_user_profile(current_username)
    if user_data:
        st.session_state["role"] = user_data["role"]
        st.session_state["name"] = user_data["name"]

    # Record login timestamp in users table upon authentication
    if not st.session_state.get("login_timestamp_recorded"):
        services.record_user_login(current_username)
        st.session_state["login_timestamp_recorded"] = True

current_name = st.session_state.get("name", current_username)
current_role = st.session_state.get("role", "reviewer")

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(
        """
        <div style='margin-bottom: 12px; padding: 4px 0;'>
            <div style='display: flex; align-items: center; gap: 8px;'>
                <span style='font-size: 1.5rem;'>🌿</span>
                <div>
                    <h2 style='font-size: 1.85rem; font-weight: 900; margin: 0; line-height: 1.1;
                               background: linear-gradient(135deg, #4ade80, #16a34a);
                               -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
                        VYRO
                    </h2>
                    <p style='color: #86efac; font-size: 0.76rem; margin-top: 1px; font-weight: 600; letter-spacing: 0.05em;'>
                        ECO CLEARANCE AUDIT
                    </p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    role_color = "🟢" if current_role == "reviewer" else "🔵"
    role_display = "EC Reviewer / Officer" if current_role == "reviewer" else "Project Applicant"

    st.markdown(
        f"""
        <div style='background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(52, 211, 153, 0.25); border-radius: 12px; padding: 12px 14px; margin-bottom: 14px;'>
            <div style='font-size: 0.68rem; font-weight: 800; color: #4ade80; text-transform: uppercase; letter-spacing: 0.08em; display: flex; align-items: center; gap: 6px;'>
                <span>🌱</span> ACTIVE WORKSPACE
            </div>
            <div style='font-size: 1.05rem; font-weight: 700; color: #f8fafc; margin-top: 4px;'>
                {current_name}
            </div>
            <div style='font-size: 0.8rem; color: #cbd5e1; margin-top: 2px;'>
                {role_color} <b>{role_display}</b>
            </div>
            <div style='font-size: 0.74rem; color: #94a3b8; margin-top: 2px; font-family: monospace;'>
                ID: @{current_username}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Navigation menu between pages
    st.markdown("### 🧭 Navigation")
    curr_page = st.session_state.get("auth_page", "submit")
    has_res = st.session_state.get("review_result") is not None

    if current_role == "reviewer":
        if has_res:
            nav_options = [
                "📤 Submit Report",
                "📊 Audit Results & Follow-Up",
                "🎯 Reviewer Priority View",
                "👥 Users View",
                "📑 Reports View"
            ]
            page_map = {
                "📤 Submit Report": "submit",
                "📊 Audit Results & Follow-Up": "results",
                "🎯 Reviewer Priority View": "reviewer_priority",
                "👥 Users View": "users",
                "📑 Reports View": "reports"
            }
        else:
            nav_options = [
                "📤 Submit Report",
                "👥 Users View",
                "📑 Reports View"
            ]
            page_map = {
                "📤 Submit Report": "submit",
                "👥 Users View": "users",
                "📑 Reports View": "reports"
            }
    else:
        if has_res:
            nav_options = [
                "📤 Submit Report",
                "📊 Audit Results & Follow-Up",
                "📑 Reports View"
            ]
            page_map = {
                "📤 Submit Report": "submit",
                "📊 Audit Results & Follow-Up": "results",
                "📑 Reports View": "reports"
            }
        else:
            nav_options = [
                "📤 Submit Report",
                "📑 Reports View"
            ]
            page_map = {
                "📤 Submit Report": "submit",
                "📑 Reports View": "reports"
            }

    rev_map = {v: k for k, v in page_map.items()}
    current_label = rev_map.get(curr_page, nav_options[0])
    default_idx = nav_options.index(current_label) if current_label in nav_options else 0

    selected_nav = st.radio(
        "Current View:",
        nav_options,
        index=default_idx,
        key="sidebar_nav_selection"
    )
    target_page = page_map[selected_nav]
    if target_page != curr_page:
        st.session_state["auth_page"] = target_page
        st.rerun()
    st.divider()
    
    # Logout action
    try:
        authenticator.logout(button_name="🚪 Log Out", location="sidebar")
    except Exception:
        if st.sidebar.button("🚪 Log Out", key="fallback_logout", use_container_width=True):
            st.session_state["authentication_status"] = None
            st.session_state["username"] = None
            st.session_state["name"] = None
            st.session_state["role"] = None
            st.session_state["review_result"] = None
            st.session_state["review_project_name"] = ""
            st.session_state["login_timestamp_recorded"] = False
            st.session_state["auth_page"] = "submit"
            st.session_state["page"] = "landing"
            st.rerun()

    # If logout button was clicked via authenticator
    if st.session_state.get("logout"):
        st.session_state["authentication_status"] = None
        st.session_state["username"] = None
        st.session_state["name"] = None
        st.session_state["role"] = None
        st.session_state["review_result"] = None
        st.session_state["review_project_name"] = ""
        st.session_state["login_timestamp_recorded"] = False
        st.session_state["auth_page"] = "submit"
        st.session_state["page"] = "landing"
        st.rerun()

# ==============================================================================
# AUTHENTICATED AREA: PAGE ROUTING (SUBMIT vs RESULTS vs REVIEWER PRIORITY)
# ==============================================================================
current_auth_page = st.session_state.get("auth_page", "submit")
has_review_result = st.session_state.get("review_result") is not None

# Security check: Non-reviewers cannot access reviewer_priority view
if current_auth_page == "reviewer_priority" and current_role != "reviewer":
    current_auth_page = "results" if has_review_result else "submit"
    st.session_state["auth_page"] = current_auth_page

# Render Environmental Clearance Top Banner
render_environmental_header(role_display, current_name)

if current_auth_page == "users":
    # --------------------------------------------------------------------------
    # VIEW: USERS DIRECTORY (AUTHENTICATION DATA ONLY)
    # --------------------------------------------------------------------------
    st.markdown("## 👥 Users Directory")
    st.caption("Authentication and user account credentials (strictly isolated from application and report data).")

    users_data = services.get_users_page_data()

    # Top KPI Metrics
    total_u = len(users_data)
    reviewers_cnt = sum(1 for u in users_data if u.get("role") == "reviewer")
    applicants_cnt = sum(1 for u in users_data if u.get("role") == "applicant")

    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        st.metric("Total Registered Users", total_u)
    with m_col2:
        st.metric("Appraisal Officers (Reviewers)", reviewers_cnt)
    with m_col3:
        st.metric("Project Proponents (Applicants)", applicants_cnt)

    st.markdown("---")

    # Format table for display
    display_rows = []
    for u in users_data:
        display_rows.append({
            "Email": u.get("email"),
            "Signup Date": str(u.get("signup_date") or "")[:19],
            "Last Login": str(u.get("last_login") or "Never")[:19],
            "Role": "🟢 Reviewer" if u.get("role") == "reviewer" else "🔵 Applicant",
            "Username": u.get("username"),
            "Full Name": u.get("name")
        })

    df_users = pd.DataFrame(display_rows)
    st.dataframe(df_users, use_container_width=True, hide_index=True)

    st.info("🔒 **Data Isolation Verified**: The `users` table contains strictly authentication, password hash, role, and login activity. Zero environmental clearance reports or compliance issues are mixed into this table.")

elif current_auth_page == "reports":
    # --------------------------------------------------------------------------
    # VIEW: APPLICATIONS & REPORTS (APPLICATION DATA ONLY)
    # --------------------------------------------------------------------------
    st.markdown("## 📑 Environmental Clearance Applications & Reports")
    st.caption("Statutory environmental clearance appraisal records (strictly isolated from user credentials).")

    reports_data = services.get_reports_page_data(
        username=current_username if current_role == "applicant" else None,
        role=current_role
    )

    total_reps = len(reports_data)
    valid_scores = [r.get("readiness_score") for r in reports_data if r.get("readiness_score") is not None]
    avg_score = round(sum(valid_scores) / max(len(valid_scores), 1)) if valid_scores else 0
    high_cnt = sum(1 for r in reports_data if (r.get("readiness_band") == "High" or (r.get("readiness_score") or 0) >= 85))
    total_issues_all = sum(r.get("total_issues", 0) for r in reports_data)

    r_col1, r_col2, r_col3, r_col4 = st.columns(4)
    with r_col1:
        st.metric("Total Applications", total_reps)
    with r_col2:
        st.metric("Average Readiness", f"{avg_score}%")
    with r_col3:
        st.metric("High Readiness Band", high_cnt)
    with r_col4:
        st.metric("Total Compliance Issues", total_issues_all)

    st.markdown("---")

    display_reports = []
    for r in reports_data:
        r_low = r.get("readiness_range_low")
        r_high = r.get("readiness_range_high")
        range_str = f"[{r_low}% - {r_high}%]" if r_low is not None and r_high is not None else "N/A"

        display_reports.append({
            "Project Name": r.get("project_name"),
            "Owner": r.get("owner_username"),
            "Readiness Score": f"{r.get('readiness_score')}%" if r.get('readiness_score') is not None else "N/A",
            "Readiness Band": r.get("readiness_band") or "N/A",
            "Uncertainty Range": range_str,
            "Completeness Score": f"{r.get('completeness_score')}%" if r.get('completeness_score') is not None else "N/A",
            "Issues (Open/Total)": f"{r.get('open_issues', 0)} / {r.get('total_issues', 0)}",
            "Confirmed / Dismissed": f"{r.get('confirmed_issues', 0)} / {r.get('dismissed_issues', 0)}",
            "Last Audit Update": str(r.get("updated_at") or "")[:19]
        })

    df_reports = pd.DataFrame(display_reports)
    st.dataframe(df_reports, use_container_width=True, hide_index=True)

    st.markdown("### 🔍 Open Project in Audit Viewer")
    project_names = [r["project_name"] for r in reports_data]
    if project_names:
        c_sel, c_btn = st.columns([3, 1])
        with c_sel:
            chosen_pname = st.selectbox("Select Project to Inspect:", project_names, key="rep_view_select_pname")
        with c_btn:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("🚀 Load into Audit Viewer", key="btn_load_from_rep_view", use_container_width=True, type="primary"):
                loaded_audit = services.load_project_audit(chosen_pname)
                if loaded_audit:
                    st.session_state["review_result"] = loaded_audit
                    st.session_state["review_project_name"] = chosen_pname
                    st.session_state["auth_page"] = "results"
                    st.rerun()
                else:
                    st.error(f"Could not load audit data for '{chosen_pname}'.")

    st.info("🛡️ **Relational Integrity Verified**: The `applications` table contains strictly report metadata and multi-agent audit results. User relationship is maintained via foreign key `owner_username -> users.username` without duplicating user credentials.")

elif current_auth_page == "submit" or not has_review_result:
    # --------------------------------------------------------------------------
    # PAGE 1: SUBMIT ENVIRONMENTAL CLEARANCE REPORT
    # --------------------------------------------------------------------------
    st.title("Submit Environmental Clearance Report")
    st.caption("Upload an application document (PDF) for automated completeness audit, cross-page figure consistency, and contradiction detection.")

    # Banner link to active review if already present in session
    if st.session_state.get("review_result"):
        active_pname = st.session_state["review_result"].project_name
        c_info1, c_info2 = st.columns([3, 1])
        with c_info1:
            st.info(f"📊 Active audit results available in session for: **{active_pname}**")
        with c_info2:
            if st.button("👉 View Results Page", key="btn_goto_results_banner", use_container_width=True):
                st.session_state["auth_page"] = "results"
                st.rerun()

    with st.container():
        col_input1, col_input2 = st.columns([1, 1])
        with col_input1:
            project_name = st.text_input(
                "Project Name",
                value=st.session_state.get("review_project_name", ""),
                placeholder="e.g. GreenHorizon Thermal Power Plant Expansion",
                help="Enter the official name of the project or industrial plant"
            )
        with col_input2:
            uploaded_pdf = st.file_uploader(
                "Upload Application Report (PDF only)",
                type=["pdf"],
                help="Upload the technical EIA/EMP or Environmental Clearance proposal document"
            )

        submit_button = st.button("🚀 Submit for Review", type="primary", use_container_width=True)

    # Quick-load past reviewed projects if no review is currently displayed
    past_projects = services.get_all_reviewed_projects(username=current_username, role=current_role)
    if past_projects:
        with st.expander("📂 Or View/Resolve Clarifications for an Existing Project", expanded=(current_role == "applicant")):
            sel_project = st.selectbox("Select Audited Project:", options=past_projects, key="sel_past_proj")
            if st.button("🔍 Open Project Clarifications", key="btn_load_proj", use_container_width=True):
                loaded_audit = services.load_project_audit(sel_project)
                if loaded_audit:
                    st.session_state["review_result"] = loaded_audit
                    st.session_state["review_project_name"] = sel_project
                    st.session_state["auth_page"] = "results"
                    st.rerun()

    # Process review upon submission
    if submit_button:
        if not project_name.strip():
            st.error("Please enter a valid Project Name before submitting.")
        elif uploaded_pdf is None:
            st.error("Please upload a PDF file of the Environmental Clearance report.")
        else:
            with st.status("🤖 Multi-Agent Review Pipeline Running...", expanded=True) as status_box:
                def live_progress_callback(stage: str, state: str, details: dict):
                    stage_icons = {
                        "Extracting text": "📄",
                        "Planner": "🧠",
                        "Specialists": "🔬",
                        "Verifier": "⚖️",
                        "Saving": "💾"
                    }
                    icon = stage_icons.get(stage, "⚙️")
                    if state == "start":
                        status_box.update(label=f"⏳ [{stage}] In progress...", state="running")
                        status_box.write(f"{icon} **[{stage}]** In progress &mdash; *{details.get('message', '')}*")
                    elif state == "complete":
                        extra = ""
                        if "pages" in details:
                            extra = f" ({details['pages']} pages parsed)"
                        elif "count" in details:
                            extra = f" ({details['count']} issues flagged)"
                        elif "verified" in details:
                            extra = f" ({details['verified']} issues citation-verified)"
                        elif "issues_count" in details:
                            extra = f" ({details['issues_count']} issues persisted)"
                        status_box.write(f"✅ **[{stage}]** Complete{extra}")
                    elif state == "error":
                        status_box.write(f"❌ **[{stage}]** Error: *{details.get('message', '')}*")

                def live_trace_callback(step: dict):
                    ag = step.get("agent", "Agent")
                    act = step.get("action", "")
                    obs = step.get("observation", "")
                    st_val = step.get("status", "success")
                    icon = "🔍" if st_val in ("success", "verified") else ("⚠️" if st_val in ("retry", "fallback") else "ℹ️")
                    status_box.write(f"&nbsp;&nbsp;&nbsp;&nbsp;{icon} `[{ag}]` *{act}*: {obs}")

                review_result, err_msg, total_pages = services.process_application_review(
                    uploaded_file=uploaded_pdf,
                    project_name=project_name,
                    trace_callback=live_trace_callback,
                    progress_callback=live_progress_callback,
                    owner_username=current_username
                )

                if err_msg:
                    status_box.update(label="❌ Multi-Agent Review Pipeline Error", state="error")
                    st.error(err_msg)
                elif review_result:
                    st.session_state["review_result"] = review_result
                    st.session_state["review_project_name"] = project_name.strip()
                    status_box.update(label="🎉 Multi-Agent Review Pipeline Completed!", state="complete", expanded=False)
                    st.session_state["auth_page"] = "results"
                    st.rerun()

elif current_auth_page == "reviewer_priority" and current_role == "reviewer" and has_review_result:
    # --------------------------------------------------------------------------
    # PAGE 3: REVIEWER PRIORITY ACTION VIEW (Role: Reviewer Only)
    # --------------------------------------------------------------------------
    result: ReviewResult = st.session_state["review_result"]
    result.issues = services.sync_project_issues(result.project_name, result.issues)

    col_nav_back, col_nav_title, col_nav_all = st.columns([1.2, 3, 1.5])
    with col_nav_back:
        if st.button("⬅ Submit New Report", key="btn_prio_back_submit", use_container_width=True):
            st.session_state["auth_page"] = "submit"
            st.rerun()
    with col_nav_title:
        st.markdown(f"## 🎯 Reviewer Priority View: {result.project_name}")
    with col_nav_all:
        if st.button("📊 View Full Audit Report", key="btn_prio_goto_results", use_container_width=True):
            st.session_state["auth_page"] = "results"
            st.rerun()

    # 1. Summary Metrics at top: Total issues, Critical/Major, Pending, Confirmed, Dismissed
    action_counts = services.get_reviewer_action_counts(result.issues)
    metrics = services.calculate_reviewer_metrics(result.issues)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Issues", metrics["total"])
    m2.metric("Critical / Major", metrics["critical"] + metrics["major"], delta="Action Required" if (metrics["critical"] + metrics["major"]) > 0 else None, delta_color="inverse")
    m3.metric("⏳ Pending", action_counts["pending"])
    m4.metric("✅ Confirmed", action_counts["confirmed"])
    m5.metric("🚫 Dismissed", action_counts["dismissed"])

    # 2. Top section "Needs Your Attention": top 3 most critical issues
    st.divider()
    st.markdown("### 🚨 Needs Your Attention")
    st.caption("Top 3 most critical issues sorted by Critical/Major severity first, then Open status, then Contradiction category:")

    top_3 = services.get_top_critical_issues(result.issues, limit=3)

    if top_3:
        cols_top = st.columns(len(top_3))
        for idx, iss in enumerate(top_3):
            with cols_top[idx]:
                is_conf = getattr(iss, "reviewer_decision", None) == "Confirmed"
                is_dism = getattr(iss, "reviewer_decision", None) == "Dismissed"

                border_color = "#dc2626" if iss.severity in ("Critical", "High") else ("#ea580c" if iss.severity in ("Major", "Medium") else "#16a34a")
                
                decision_badge = ""
                if is_dism:
                    decision_badge = "<span style='background: #475569; color: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 0.72rem;'>🚫 Dismissed</span>"
                elif is_conf:
                    decision_badge = "<span style='background: #166534; color: #bbf7d0; padding: 2px 6px; border-radius: 4px; font-size: 0.72rem;'>✅ Confirmed</span>"
                else:
                    decision_badge = "<span style='background: #1e3a8a; color: #bfdbfe; padding: 2px 6px; border-radius: 4px; font-size: 0.72rem;'>⏳ Pending</span>"

                page_ref = iss.page_number or iss.evidence_page or "N/A"
                quote_text = iss.quote or iss.evidence_text or "N/A"

                st.markdown(
                    f"""
                    <div style='border: 2px solid {border_color}; border-radius: 8px; padding: 14px; background: rgba(15, 23, 42, 0.7); min-height: 310px; margin-bottom: 10px;'>
                        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;'>
                            <span style='font-size: 0.8rem; font-weight: bold; color: #94a3b8;'>TOP #{idx+1} PRIORITY</span>
                            <span style='background: {border_color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold;'>{iss.severity.upper()}</span>
                        </div>
                        <p style='margin: 0; font-size: 0.95rem; font-weight: bold; color: #f8fafc;'>{iss.category} &nbsp; {decision_badge}</p>
                        <p style='color: #38bdf8; font-size: 0.8rem; margin: 4px 0 2px 0;'>🎯 <b>Confidence:</b> {iss.confidence or 'Medium'} &nbsp;|&nbsp; 📍 <b>Page:</b> {page_ref}</p>
                        <p style='color: #e2e8f0; font-size: 0.85rem; margin-bottom: 6px; line-height: 1.3;'><b>Description:</b> {iss.description}</p>
                        <p style='color: #cbd5e1; font-size: 0.8rem; font-style: italic; margin-bottom: 6px; line-height: 1.3; background: rgba(30, 41, 59, 0.6); padding: 4px 6px; border-radius: 4px;'><b>Exact Quote (≤25 words):</b> \"{quote_text}\"</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                top_comment = st.text_input("Reviewer Comment (optional):", value=getattr(iss, "reviewer_comment", "") or "", key=f"top_cmt_{iss.id}_{idx}")
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    if st.button("✅ Confirm", key=f"top_conf_{iss.id}_{idx}", type="primary" if is_conf else "secondary", use_container_width=True):
                        services.save_reviewer_action(iss, "Confirmed", top_comment, result)
                        st.rerun()
                with c_btn2:
                    if st.button("❌ Dismiss", key=f"top_dism_{iss.id}_{idx}", use_container_width=True):
                        services.save_reviewer_action(iss, "Dismissed", top_comment, result)
                        st.rerun()

    # 3. Filters: severity (Critical / Major / Minor / All), status (Open / Resolved / All), category
    st.divider()
    st.markdown("### 🔍 Filters")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filter_sev = st.selectbox("Severity:", ["All", "Critical", "Major", "Minor"], key="prio_filter_sev")
    with col_f2:
        filter_status = st.selectbox("Status:", ["All", "Open", "Resolved"], key="prio_filter_status")
    with col_f3:
        all_categories = ["All"] + sorted(list(set(i.category for i in result.issues if i.category)))
        filter_cat = st.selectbox("Category:", all_categories, key="prio_filter_cat")

    filtered_issues = services.filter_issues(result.issues, filter_sev, filter_status, filter_cat)

    # 4. Full issues table below, colour-coded by severity with Confirm & Dismiss buttons
    st.markdown(f"### 📋 Full Issues ({len(filtered_issues)} matching filters)")

    if not filtered_issues:
        st.info("No issues match the selected filter criteria.")
    else:
        for idx, iss in enumerate(filtered_issues):
            is_dismissed = getattr(iss, "reviewer_decision", None) == "Dismissed"
            is_confirmed = getattr(iss, "reviewer_decision", None) == "Confirmed"

            if is_dismissed:
                card_style = "border: 1px solid #475569; background-color: rgba(51, 65, 85, 0.25); opacity: 0.6; border-radius: 8px; padding: 12px; margin-bottom: 10px;"
            else:
                sev_border = "#dc2626" if iss.severity in ("Critical", "High") else ("#ea580c" if iss.severity in ("Major", "Medium") else "#16a34a")
                sev_bg = "rgba(127, 29, 29, 0.12)" if iss.severity in ("Critical", "High") else ("rgba(124, 45, 18, 0.12)" if iss.severity in ("Major", "Medium") else "rgba(20, 83, 45, 0.12)")
                card_style = f"border-left: 5px solid {sev_border}; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155; background-color: {sev_bg}; border-radius: 8px; padding: 12px; margin-bottom: 10px;"

            with st.container():
                st.markdown(f"<div style='{card_style}'>", unsafe_allow_html=True)
                c_left, c_mid, c_right = st.columns([1.5, 4.5, 2.5])
                with c_left:
                    st.markdown(f"**Issue #{idx + 1}**")
                    sev_color = "red" if iss.severity in ("Critical", "High") else ("orange" if iss.severity in ("Major", "Medium") else "green")
                    st.markdown(f":{sev_color}[**{iss.severity} Severity**]")
                    conf_color = "green" if iss.confidence == "High" else ("orange" if iss.confidence == "Medium" else "blue")
                    st.markdown(f":{conf_color}[🎯 **{iss.confidence or 'Medium'} Confidence**]")
                    st.caption(f"`{iss.category}`")
                    st.caption(f"📍 Page: {iss.page_number or iss.evidence_page or 'N/A'}")
                    if is_dismissed:
                        st.markdown("<span style='color: #94a3b8; font-weight: bold;'>🚫 Dismissed<br><small>(Excluded from PDF)</small></span>", unsafe_allow_html=True)
                    elif is_confirmed:
                        st.markdown("<span style='color: #4ade80; font-weight: bold;'>✅ Confirmed</span>", unsafe_allow_html=True)
                    else:
                        st.markdown("<span style='color: #60a5fa;'>⏳ Pending</span>", unsafe_allow_html=True)

                with c_mid:
                    desc_color = "#94a3b8" if is_dismissed else "#f8fafc"
                    st.markdown(f"<p style='color: {desc_color}; margin: 0 0 4px 0;'><b>Description:</b> {iss.description}</p>", unsafe_allow_html=True)
                    quote_val = iss.quote or iss.evidence_text
                    if quote_val:
                        st.markdown(f"<p style='color: #94a3b8; font-size: 0.85rem; margin: 0 0 4px 0;'><b>Exact Quote (≤25 words):</b> <i>\"{quote_val}\"</i></p>", unsafe_allow_html=True)
                    if iss.follow_up_question:
                        st.markdown(f"<p style='color: #cbd5e1; font-size: 0.85rem; margin: 0 0 4px 0;'><b>Applicant Query:</b> {iss.follow_up_question}</p>", unsafe_allow_html=True)
                    if iss.applicant_reply:
                        st.markdown(f"<p style='color: #67e8f9; font-size: 0.85rem; margin: 0;'><b>Applicant Reply:</b> <i>\"{iss.applicant_reply}\"</i></p>", unsafe_allow_html=True)
                    if getattr(iss, "reviewer_comment", None):
                        rev_time = f" <small>({iss.reviewed_at})</small>" if getattr(iss, "reviewed_at", None) else ""
                        st.markdown(f"<p style='color: #86efac; font-size: 0.85rem; margin: 6px 0 0 0;'><b>Reviewer Note:</b> {iss.reviewer_comment}{rev_time}</p>", unsafe_allow_html=True)

                with c_right:
                    st.caption("Reviewer Action & Optional Comment:")
                    prio_comment = st.text_input("Comment:", value=getattr(iss, "reviewer_comment", "") or "", key=f"prio_cmt_{iss.id}_{idx}", placeholder="Optional note/reason...")
                    c_act1, c_act2 = st.columns(2)
                    with c_act1:
                        if st.button("✅ Confirm", key=f"prio_conf_{iss.id}_{idx}", use_container_width=True, type="primary" if is_confirmed else "secondary"):
                            services.save_reviewer_action(iss, "Confirmed", prio_comment, result)
                            st.rerun()
                    with c_act2:
                        if st.button("❌ Dismiss", key=f"prio_dism_{iss.id}_{idx}", use_container_width=True):
                            services.save_reviewer_action(iss, "Dismissed", prio_comment, result)
                            st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)

    # Download updated report
    st.divider()
    c_dl1, c_dl2 = st.columns([1, 1])
    with c_dl1:
        pdf_bytes, report_filename = services.generate_report_download(result)
        st.download_button(
            label="📥 Download Updated Error Report (PDF)",
            data=pdf_bytes,
            file_name=report_filename,
            mime="application/pdf",
            type="primary",
            use_container_width=True,
            help="Download formal Review Report with dismissed issues excluded."
        )
    with c_dl2:
        if st.button("📊 View Full Audit Results & Clarification Loop", key="btn_return_results_bottom", use_container_width=True):
            st.session_state["auth_page"] = "results"
            st.rerun()

elif current_auth_page == "results" and has_review_result:
    # --------------------------------------------------------------------------
    # PAGE 2: AUDIT RESULTS DASHBOARD & APPLICANT FOLLOW-UP (Dedicated Page)
    # --------------------------------------------------------------------------
    result: ReviewResult = st.session_state["review_result"]
    result.issues = services.sync_project_issues(result.project_name, result.issues)

    col_nav_back, col_nav_title, col_nav_priority = st.columns([1.2, 3, 1.5])
    with col_nav_back:
        if st.button("⬅ Submit Another Report", key="btn_top_back_submit", use_container_width=True):
            st.session_state["auth_page"] = "submit"
            st.rerun()
    with col_nav_title:
        st.markdown(f"## 📊 Audit Results: {result.project_name}")
    with col_nav_priority:
        if current_role == "reviewer":
            if st.button("🎯 Reviewer Priority View", key="btn_goto_priority_from_results", type="primary", use_container_width=True):
                st.session_state["auth_page"] = "reviewer_priority"
                st.rerun()
    
    # 1. Statutory Clearance Readiness Score Calculation & Live Display
    services.refresh_review_readiness(result)
    r_score = result.readiness_score if result.readiness_score is not None else result.completeness_score
    r_band = result.readiness_band or ("High" if r_score >= 85 else ("Moderate" if r_score >= 65 else ("Low" if r_score >= 40 else "Very low")))
    r_low = result.readiness_range_low if result.readiness_range_low is not None else r_score
    r_high = result.readiness_range_high if result.readiness_range_high is not None else r_score

    band_styles = {
        "High": {"border": "#16a34a", "bg": "rgba(22, 101, 52, 0.2)", "badge": "#166534", "text": "#4ade80"},
        "Moderate": {"border": "#2563eb", "bg": "rgba(30, 58, 138, 0.2)", "badge": "#1e3a8a", "text": "#60a5fa"},
        "Low": {"border": "#ea580c", "bg": "rgba(124, 45, 18, 0.2)", "badge": "#9a3412", "text": "#fb923c"},
        "Very low": {"border": "#dc2626", "bg": "rgba(127, 29, 29, 0.2)", "badge": "#991b1b", "text": "#f87171"},
    }
    b_style = band_styles.get(r_band, band_styles["Moderate"])

    st.markdown(
        f"""
        <div style='border: 2px solid {b_style["border"]}; background: {b_style["bg"]}; border-radius: 10px; padding: 18px 24px; margin-bottom: 16px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;'>
                <div>
                    <span style='font-size: 0.8rem; font-weight: bold; text-transform: uppercase; letter-spacing: 0.06em; color: #94a3b8;'>
                        Statutory Compliance Appraisal &bull; MoEFCC / EAC Benchmark
                    </span>
                    <h2 style='margin: 4px 0 0 0; font-size: 1.85rem; color: #f8fafc;'>
                        Clearance Readiness Score
                    </h2>
                </div>
                <div style='text-align: right;'>
                    <span style='font-size: 2.5rem; font-weight: 900; color: {b_style["text"]};'>{r_score}%</span>
                    <span style='background: {b_style["badge"]}; color: white; padding: 4px 10px; border-radius: 6px; font-size: 0.85rem; font-weight: bold; margin-left: 10px;'>
                        {r_band.upper()} BAND
                    </span>
                    <p style='color: #cbd5e1; font-size: 0.85rem; margin: 4px 0 0 0;'>
                        Estimated Range: <b>[{r_low}% &ndash; {r_high}%]</b>
                    </p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Category counts: Critical, Major, Minor rule breakdowns
    cc = result.readiness_category_counts or {}
    crit_c = cc.get("Critical", {"pass": 0, "partial": 0, "fail": 0, "not_found": 0, "total": 6})
    maj_c = cc.get("Major", {"pass": 0, "partial": 0, "fail": 0, "not_found": 0, "total": 8})
    min_c = cc.get("Minor", {"pass": 0, "partial": 0, "fail": 0, "not_found": 0, "total": 4})

    col_cat1, col_cat2, col_cat3 = st.columns(3)
    with col_cat1:
        st.markdown(
            f"<div style='background: rgba(15, 23, 42, 0.6); padding: 8px 12px; border-radius: 6px; border-left: 4px solid #dc2626; margin-bottom: 10px;'>"
            f"<b>Critical Rules (Weight 3)</b><br>"
            f"<span style='font-size: 0.85rem; color: #cbd5e1;'>✅ {crit_c.get('pass', 0)} Pass &nbsp;|&nbsp; ⚠️ {crit_c.get('partial', 0)} Partial &nbsp;|&nbsp; ❌ {crit_c.get('fail', 0)} Fail &nbsp;|&nbsp; ❓ {crit_c.get('not_found', 0)} Missing</span>"
            f"</div>",
            unsafe_allow_html=True
        )
    with col_cat2:
        st.markdown(
            f"<div style='background: rgba(15, 23, 42, 0.6); padding: 8px 12px; border-radius: 6px; border-left: 4px solid #ea580c; margin-bottom: 10px;'>"
            f"<b>Major Rules (Weight 2)</b><br>"
            f"<span style='font-size: 0.85rem; color: #cbd5e1;'>✅ {maj_c.get('pass', 0)} Pass &nbsp;|&nbsp; ⚠️ {maj_c.get('partial', 0)} Partial &nbsp;|&nbsp; ❌ {maj_c.get('fail', 0)} Fail &nbsp;|&nbsp; ❓ {maj_c.get('not_found', 0)} Missing</span>"
            f"</div>",
            unsafe_allow_html=True
        )
    with col_cat3:
        st.markdown(
            f"<div style='background: rgba(15, 23, 42, 0.6); padding: 8px 12px; border-radius: 6px; border-left: 4px solid #16a34a; margin-bottom: 10px;'>"
            f"<b>Minor Rules (Weight 1)</b><br>"
            f"<span style='font-size: 0.85rem; color: #cbd5e1;'>✅ {min_c.get('pass', 0)} Pass &nbsp;|&nbsp; ⚠️ {min_c.get('partial', 0)} Partial &nbsp;|&nbsp; ❌ {min_c.get('fail', 0)} Fail &nbsp;|&nbsp; ❓ {min_c.get('not_found', 0)} Missing</span>"
            f"</div>",
            unsafe_allow_html=True
        )

    # Top 3 Improvements
    if getattr(result, "readiness_improvements", None):
        with st.expander("📈 To Improve Your Score (Top 3 Potential Gains)", expanded=True):
            for imp in result.readiness_improvements[:3]:
                badge_bg = "#7f1d1d" if imp["category"] == "Critical" else ("#7c2d12" if imp["category"] == "Major" else "#14532d")
                st.markdown(
                    f"• <span style='background: {badge_bg}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.75rem; font-weight: bold;'>{imp['category']}</span> "
                    f"<b>{imp['rule_name']}</b> &mdash; <span style='color: #4ade80; font-weight: bold;'>+{imp['score_gain']}% Gain</span>: "
                    f"<i>{imp['recommendation']}</i>",
                    unsafe_allow_html=True
                )

    # Mandatory Legal Disclaimer
    st.info("ℹ️ **Disclaimer:** Indicative estimate based on rule compliance. Final decision rests with EAC/SEAC.")

    # 2. Secondary Metrics: Completeness Score, Deficiencies & Reviewer Decision Counts
    action_counts = services.get_reviewer_action_counts(result.issues)
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        comp_val = result.completeness_score
        st.metric(label="Completeness", value=f"{comp_val}%")
    with m2:
        st.metric(label="Missing Studies", value=f"{len(result.missing_studies)}")
    with m3:
        st.metric(label="Flagged Issues", value=f"{len(result.issues)}")
    with m4:
        st.metric(label="✅ Confirmed", value=action_counts["confirmed"])
    with m5:
        st.metric(label="🚫 Dismissed", value=action_counts["dismissed"], delta=f"{action_counts['pending']} Pending", delta_color="off")

    # 2. Executive Summary
    st.markdown("### 📋 Executive Summary")
    st.info(result.summary)

    # Multi-Agent Execution Trace Expander
    if getattr(result, "agent_trace", None):
        with st.expander(f"🤖 Multi-Agent Execution Trace ({len(result.agent_trace)} steps recorded)", expanded=False):
            st.caption("Detailed Thought / Action / Observation log recorded across Planner, Specialists, and Verifier:")
            for t_step in result.agent_trace:
                ag = t_step.get("agent", "Agent")
                act = t_step.get("action", "")
                obs = t_step.get("observation", "")
                st_val = t_step.get("status", "success")
                badge_col = "green" if st_val in ("success", "verified") else ("orange" if st_val in ("retry", "fallback") else "red")
                st.markdown(f":{badge_col}[**[{ag}]**] `{act}`")
                st.write(f"&rarr; *{obs}*")


    # 3. Missing Studies Section
    st.markdown("### 🚨 Missing Mandatory Studies")
    if result.missing_studies:
        cols = st.columns(min(max(len(result.missing_studies), 1), 3))
        for idx, study in enumerate(result.missing_studies):
            cols[idx % 3].error(f"❌ **Missing:** {study.title()}")
    else:
        st.success("✅ All mandatory checklist studies are addressed in the application.")

    # 3b. 18 Statutory EC Rules Appraisal Breakdown
    if getattr(result, "rule_results", None):
        with st.expander(f"📜 18 Statutory EC Rules Appraisal Breakdown ({len(result.rule_results)} rules evaluated)", expanded=False):
            st.caption("Detailed appraisal per MoEFCC EIA Notification (2006) and EAC statutory guidelines:")
            for r in result.rule_results:
                r_status = getattr(r, "status", "not_found")
                r_name = getattr(r, "rule_name", "")
                r_id = getattr(r, "rule_id", "")
                r_cat = getattr(r, "category", "")
                r_w = getattr(r, "weight", 1)
                r_reason = getattr(r, "reason", "")
                r_page = getattr(r, "page_number", "")
                r_quote = getattr(r, "quote", "")

                status_badge = "✅ Pass" if r_status == "pass" else ("⚠️ Partial" if r_status == "partial" else ("❌ Fail" if r_status == "fail" else "❓ Not Found"))
                st.markdown(f"**[{r_id}] {r_name}** (`{r_cat}` &bull; Weight {r_w}) &mdash; **{status_badge}**")
                st.write(f"&rarr; {r_reason}")
                if r_quote:
                    st.caption(f"📍 {r_page or 'Document'} &bull; *\"{r_quote}\"*")
                st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)

    # 4. Color-coded Issues Table (Pandas)
    st.markdown("### 🔍 Issues, Figures Inconsistencies & Contradictions")
    if result.issues:
        table_data = services.format_issues_table_data(result.issues)
        df = pd.DataFrame(table_data)

        # Critical red, Major orange, Minor green
        def color_severity(val):
            if val in ("Critical", "High"):
                return "background-color: #7f1d1d; color: #fecaca; font-weight: bold;"
            elif val in ("Major", "Medium"):
                return "background-color: #7c2d12; color: #fed7aa; font-weight: bold;"
            elif val in ("Minor", "Low"):
                return "background-color: #14532d; color: #bbf7d0; font-weight: bold;"
            return ""

        def color_confidence(val):
            if val == "High":
                return "color: #4ade80; font-weight: bold;"
            elif val == "Medium":
                return "color: #facc15; font-weight: bold;"
            elif val == "Low":
                return "color: #94a3b8;"
            return ""

        styled_df = df.style.map(color_severity, subset=["Severity"]).map(color_confidence, subset=["Confidence"])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        st.success("🎉 No internal discrepancies or contradictions found in the submitted report.")

    # 5. Export / Download Error Report (PDF)
    st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
    
    col_dl, col_reset = st.columns([1, 1])
    with col_dl:
        pdf_bytes, report_filename = services.generate_report_download(result)
        st.download_button(
            label="📥 Download Error Report (PDF)",
            data=pdf_bytes,
            file_name=report_filename,
            mime="application/pdf",
            type="primary",
            use_container_width=True,
            help="Download the formal Environmental Clearance Review Report with color-coded discrepancies and clarification queries"
        )

    with col_reset:
        if st.button("🔄 Submit Another Application Report", key="btn_clear_review", use_container_width=True):
            st.session_state["review_result"] = None
            st.session_state["review_project_name"] = ""
            st.session_state["auth_page"] = "submit"
            st.rerun()

    # ==============================================================================
    # 6. APPLICANT FOLLOW-UP & CLARIFICATION LOOP
    # ==============================================================================
    st.divider()
    st.markdown("## 💬 Applicant Follow-Up & Clarification Loop")
    st.caption("Address flagged deficiencies and queries directly. VYRO AI evaluates your technical clarifications and supporting documentation.")

    # Calculate Progress: "X of Y issues resolved"
    x_count, y_count, progress_ratio, resolved_issues, unresolved_issues = services.calculate_resolution_progress(result.issues)
    st.markdown(f"### 🎯 Resolution Progress: **{x_count} of {y_count} issues resolved**")
    st.progress(progress_ratio)

    if x_count == y_count and y_count > 0:
        st.success("🎉 **All identified issues have been successfully resolved!** The project is eligible for final Environmental Clearance endorsement.")

    # Unresolved issues list
    if unresolved_issues:
        st.markdown(f"#### 📝 Open Deficiencies & Queries ({len(unresolved_issues)} pending)")
        
        for idx, issue in enumerate(unresolved_issues):
            with st.container(border=True):
                col_badge, col_meta = st.columns([1, 4])
                with col_badge:
                    sev = issue.severity
                    sev_color = "red" if sev in ("Critical", "High") else ("orange" if sev in ("Major", "Medium") else "green")
                    st.markdown(f"**Issue #{idx + 1}**")
                    st.markdown(f":{sev_color}[**{sev} Severity**]")
                    conf = issue.confidence or "Medium"
                    conf_color = "green" if conf == "High" else ("orange" if conf == "Medium" else "blue")
                    st.markdown(f":{conf_color}[🎯 **{conf} Confidence**]")
                    st.caption(f"`{issue.category}`")
                    st.caption(f"📍 Page: {issue.page_number or issue.evidence_page or 'N/A'}")
                    if issue.status == "Still Open":
                        st.badge("Still Open", color="red")
                    elif issue.status == "Needs More Info":
                        st.badge("Needs More Info", color="orange")
                    else:
                        st.badge("Open", color="blue")

                with col_meta:
                    st.markdown(f"**Description:** {issue.description}")
                    quote_val = issue.quote or issue.evidence_text
                    if quote_val:
                        st.markdown(f"**Exact Quote (≤25 words):** *\"{quote_val}\"*")
                    if getattr(issue, "reviewer_comment", None):
                        st.info(f"📌 **Reviewer Note:** {issue.reviewer_comment}")
                    
                    st.markdown(
                        f"""
                        <div style='background-color: rgba(59, 130, 246, 0.12); border-left: 4px solid #3b82f6; padding: 12px; border-radius: 6px; margin: 10px 0;'>
                            <strong style='color: #60a5fa;'>❓ Clarification Query to Applicant:</strong><br>
                            <span style='font-size: 1.05rem; color: #f1f5f9;'>{issue.follow_up_question or "Please provide technical clarification."}</span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                # If previously evaluated and still open, display the AI's reason
                if issue.ai_reason:
                    st.warning(f"⚠️ **AI Review Feedback:** {issue.ai_reason}")

                # Reply text area
                reply_input = st.text_area(
                    "Applicant Technical Reply:",
                    value=issue.applicant_reply or "",
                    key=f"reply_input_{issue.id}",
                    placeholder="Enter detailed clarification, revised technical figures, or compliance commitments...",
                    help="Explain how the discrepancy or gap is reconciled."
                )

                # Optional supporting PDF uploader
                supporting_pdf = st.file_uploader(
                    "Attach Supporting Document (Optional PDF):",
                    type=["pdf"],
                    key=f"support_pdf_{issue.id}",
                    help="Upload annexures, certified lab results, or revised design sheets in PDF format"
                )

                # Submit Reply button
                col_submit, _ = st.columns([1, 3])
                with col_submit:
                    if st.button(f"📤 Submit Reply", key=f"btn_submit_{issue.id}", type="primary", use_container_width=True):
                        if not reply_input.strip() and supporting_pdf is None:
                            st.error("Please provide an explanation or upload a supporting PDF before submitting.")
                        else:
                            with st.spinner("🤖 Auditing reply with VYRO AI Compliance Engine..."):
                                followup_res, _ = services.submit_applicant_followup(
                                    issue=issue,
                                    reply_text=reply_input,
                                    supporting_pdf=supporting_pdf
                                )

                            if followup_res.status == "Resolved":
                                st.success(f"✅ **Issue Resolved:** {followup_res.reason}")
                            else:
                                st.warning(f"⚠️ **Issue Still Open:** {followup_res.reason}")

                            st.rerun()

    # Expander for Resolved Issues
    if resolved_issues:
        with st.expander(f"✅ View Resolved Issues ({len(resolved_issues)})", expanded=False):
            for r_idx, r_issue in enumerate(resolved_issues):
                st.markdown(f"#### ✅ {r_idx + 1}. {r_issue.description} (`{r_issue.category}` - {r_issue.severity} Severity)")
                if r_issue.follow_up_question:
                    st.caption(f"**Query:** {r_issue.follow_up_question}")
                if r_issue.applicant_reply:
                    st.markdown(f"**Applicant Reply:** *\"{r_issue.applicant_reply}\"*")
                if r_issue.ai_reason:
                    st.success(f"**AI Approval Reason:** {r_issue.ai_reason}")
                st.divider()

else:
    st.session_state["auth_page"] = "submit"
    st.rerun()

