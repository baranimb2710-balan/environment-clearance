"""
Main Streamlit application for the Environmental Clearance Application Review System (VYRO).
Pure Streamlit frontend with direct SQLite & bcrypt authentication.
Includes Landing page, Authentication, and Report Submission & AI Review pipeline.
"""
import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
import db
import extract
import review
import report
from models import UserRole, ReviewResult
from landing import render_landing_page

# Page configuration
st.set_page_config(
    page_title="VYRO - Environmental Clearance Review",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 1. Initialize SQLite database & default demo reviewer
db.init_db()

# 2. Load latest credentials from SQLite
credentials = db.get_authenticator_credentials()

# 3. Setup Streamlit Authenticator
authenticator = stauth.Authenticate(
    credentials=credentials,
    cookie_name="ec_review_auth_cookie",
    cookie_key="ec_jwt_secret_token_key_review_app_2026",
    cookie_expiry_days=1.0,
    auto_hash=False  # Passwords are already hashed with bcrypt in SQLite
)

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

        col_a, col_b, col_c = st.columns([1, 2, 1])
        with col_b:
            st.markdown(
                """
                <div style='text-align: center; margin-bottom: 20px;'>
                    <h2 style='font-size: 2.6rem; font-weight: 900; margin: 0;
                               background: linear-gradient(135deg, #4ade80, #16a34a);
                               -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
                        VYRO
                    </h2>
                    <p style='color: #94a3b8; font-size: 1rem; margin-top: 4px;'>Environmental Clearance Application Review</p>
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
                    user_info = db.get_user(username)
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
                        if not new_name.strip() or not new_username.strip() or not new_email.strip():
                            st.error("All fields are mandatory.")
                        elif len(new_password) < 6:
                            st.error("Password must be at least 6 characters long.")
                        elif new_password != new_confirm_password:
                            st.error("Passwords do not match.")
                        else:
                            success, message = db.create_user(
                                username=new_username,
                                name=new_name,
                                email=new_email,
                                plain_password=new_password,
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
    user_data = db.get_user(current_username)
    if user_data:
        st.session_state["role"] = user_data["role"]
        st.session_state["name"] = user_data["name"]

current_name = st.session_state.get("name", current_username)
current_role = st.session_state.get("role", "reviewer")

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(
        """
        <div style='margin-bottom: 10px;'>
            <h2 style='font-size: 1.8rem; font-weight: 900; margin: 0;
                       background: linear-gradient(135deg, #4ade80, #16a34a);
                       -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
                VYRO
            </h2>
            <p style='color: #94a3b8; font-size: 0.85rem; margin-top: 2px;'>EC Review System</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.divider()
    st.markdown(f"**Logged in as:**\n### {current_name}")
    
    role_color = "🟢" if current_role == "reviewer" else "🔵"
    role_display = "EC Reviewer / Officer" if current_role == "reviewer" else "Project Applicant"
    st.markdown(f"**Role:** {role_color} `{role_display}`")
    st.caption(f"Username: `{current_username}`")
    st.divider()

    # Navigation menu between pages
    if st.session_state.get("review_result"):
        st.markdown("### 🧭 Navigation")
        curr_page = st.session_state.get("auth_page", "submit")
        if current_role == "reviewer":
            nav_options = ["📤 Submit Report", "📊 Audit Results & Follow-Up", "🎯 Reviewer Priority View"]
            page_map = {
                "📤 Submit Report": "submit",
                "📊 Audit Results & Follow-Up": "results",
                "🎯 Reviewer Priority View": "reviewer_priority"
            }
        else:
            nav_options = ["📤 Submit Report", "📊 Audit Results & Follow-Up"]
            page_map = {
                "📤 Submit Report": "submit",
                "📊 Audit Results & Follow-Up": "results"
            }
            if curr_page == "reviewer_priority":
                curr_page = "results"
                st.session_state["auth_page"] = "results"

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

if not has_review_result or current_auth_page == "submit":
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
    past_projects = db.get_all_projects_with_followups()
    if past_projects:
        with st.expander("📂 Or View/Resolve Clarifications for an Existing Project", expanded=(current_role == "applicant")):
            sel_project = st.selectbox("Select Audited Project:", options=past_projects, key="sel_past_proj")
            if st.button("🔍 Open Project Clarifications", key="btn_load_proj", use_container_width=True):
                records = db.get_project_followups(sel_project)
                if records:
                    loaded_issues = []
                    missing_st = []
                    for r in records:
                        iss = Issue(
                            id=r["issue_id"],
                            category=r["category"] or "Inconsistency",
                            severity=r["severity"] or "Medium",
                            description=r["description"] or "",
                            evidence_page=r["evidence_page"],
                            evidence_text=r["evidence_text"],
                            follow_up_question=r["follow_up_question"],
                            status=r["status"] or "Open",
                            applicant_reply=r["applicant_reply"],
                            ai_reason=r["ai_reason"],
                            reviewer_decision=r.get("reviewer_decision", "Pending") or "Pending"
                        )
                        loaded_issues.append(iss)
                        if iss.category == "Missing Study":
                            clean_m = iss.description.replace("Missing mandatory study: ", "").strip()
                            if clean_m and clean_m not in missing_st:
                                missing_st.append(clean_m)

                    resolved_c = sum(1 for i in loaded_issues if i.status == "Resolved")
                    calc_score = min(95, max(30, int((len(loaded_issues) - (len(loaded_issues) - resolved_c)) / max(len(loaded_issues), 1) * 100)))

                    st.session_state["review_result"] = ReviewResult(
                        project_name=sel_project,
                        completeness_score=calc_score,
                        missing_studies=missing_st,
                        issues=loaded_issues,
                        summary=f"Audit loaded from database for '{sel_project}'. Contains {len(loaded_issues)} tracked compliance issues."
                    )
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
            # Step 1: Extract text using PyMuPDF
            with st.spinner("📄 Extracting page-by-page text from PDF using PyMuPDF..."):
                extracted_text, total_pages = extract.extract_text(uploaded_pdf)

            if not extracted_text:
                st.warning(
                    "⚠️ **Scanned or Image-Only PDF Detected:** "
                    "The uploaded document contains no extractable digital text. "
                    "Per system guidelines, OCR is disabled. Please upload a report containing digital selectable text."
                )
            else:
                st.info(f"Extracted {total_pages} page(s) with digital text. Initiating AI consistency audit...")
                
                # Step 2: Review using Anthropic Claude Engine
                with st.spinner("🔍 Auditing application with VYRO AI Engine (checking mandatory checklist, figure cross-checks, contradictions)..."):
                    try:
                        review_result = review.review_application(extracted_text, project_name=project_name.strip())
                        # Sync issues with SQLite followups table
                        review_result.issues = db.sync_review_issues(project_name.strip(), review_result.issues)
                        st.session_state["review_result"] = review_result
                        st.session_state["review_project_name"] = project_name.strip()
                        # Navigate immediately to the dedicated Results Page
                        st.session_state["auth_page"] = "results"
                        st.rerun()
                    except Exception as err:
                        st.error(f"❌ Review error: {err}")

elif current_auth_page == "reviewer_priority" and current_role == "reviewer" and has_review_result:
    # --------------------------------------------------------------------------
    # PAGE 3: REVIEWER PRIORITY ACTION VIEW (Role: Reviewer Only)
    # --------------------------------------------------------------------------
    result: ReviewResult = st.session_state["review_result"]
    result.issues = db.sync_review_issues(result.project_name, result.issues)

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

    # 1. Summary Metrics at top: Total issues, High, Open, Confirmed, Dismissed
    total_issues_count = len(result.issues)
    high_count = sum(1 for i in result.issues if i.severity == "High")
    open_count = sum(1 for i in result.issues if i.status in ("Open", "Still Open"))
    confirmed_count = sum(1 for i in result.issues if getattr(i, "reviewer_decision", None) == "Confirmed")
    dismissed_count = sum(1 for i in result.issues if getattr(i, "reviewer_decision", None) == "Dismissed")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Issues", total_issues_count)
    m2.metric("High Severity", high_count, delta="Critical" if high_count > 0 else None, delta_color="inverse")
    m3.metric("Open Status", open_count)
    m4.metric("Confirmed", confirmed_count)
    m5.metric("Dismissed", dismissed_count)

    # 2. Top section "Needs Your Attention": top 3 most critical issues
    # (sort: High severity first, then Open status, then Contradiction category first)
    st.divider()
    st.markdown("### 🚨 Needs Your Attention")
    st.caption("Top 3 most critical issues sorted by High severity first, then Open status, then Contradiction category:")

    def priority_sort_key(iss):
        sev_rank = {"High": 0, "Medium": 1, "Low": 2}.get(iss.severity, 3)
        status_rank = 0 if iss.status in ("Open", "Still Open") else (1 if iss.status == "Needs More Info" else 2)
        cat_rank = 0 if iss.category == "Contradiction" else (1 if iss.category == "Inconsistency" else 2)
        return (sev_rank, status_rank, cat_rank)

    # Show top 3 critical issues, prioritizing active/un-dismissed ones
    active_critical = [i for i in result.issues if getattr(i, "reviewer_decision", None) != "Dismissed"]
    if not active_critical:
        active_critical = result.issues
    top_3 = sorted(active_critical, key=priority_sort_key)[:3]

    if top_3:
        cols_top = st.columns(len(top_3))
        for idx, iss in enumerate(top_3):
            with cols_top[idx]:
                sev_color = "red" if iss.severity == "High" else ("orange" if iss.severity == "Medium" else "green")
                is_conf = getattr(iss, "reviewer_decision", None) == "Confirmed"
                is_dism = getattr(iss, "reviewer_decision", None) == "Dismissed"

                border_color = "#dc2626" if iss.severity == "High" else ("#ea580c" if iss.severity == "Medium" else "#16a34a")
                
                decision_badge = ""
                if is_dism:
                    decision_badge = "<span style='background: #475569; color: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 0.72rem;'>🚫 Dismissed</span>"
                elif is_conf:
                    decision_badge = "<span style='background: #166534; color: #bbf7d0; padding: 2px 6px; border-radius: 4px; font-size: 0.72rem;'>✅ Confirmed</span>"
                else:
                    decision_badge = "<span style='background: #1e3a8a; color: #bfdbfe; padding: 2px 6px; border-radius: 4px; font-size: 0.72rem;'>⏳ Pending</span>"

                st.markdown(
                    f"""
                    <div style='border: 2px solid {border_color}; border-radius: 8px; padding: 14px; background: rgba(15, 23, 42, 0.7); min-height: 290px; margin-bottom: 10px;'>
                        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;'>
                            <span style='font-size: 0.8rem; font-weight: bold; color: #94a3b8;'>TOP #{idx+1} CRITICAL</span>
                            <span style='background: {border_color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold;'>{iss.severity.upper()}</span>
                        </div>
                        <p style='margin: 0; font-size: 0.95rem; font-weight: bold; color: #f8fafc;'>{iss.category} &nbsp; {decision_badge}</p>
                        <p style='color: #60a5fa; font-size: 0.8rem; margin: 4px 0 8px 0;'>📍 Page: {iss.evidence_page or 'N/A'}</p>
                        <p style='color: #e2e8f0; font-size: 0.85rem; margin-bottom: 8px; line-height: 1.3;'><b>Description:</b> {iss.description}</p>
                        <p style='color: #94a3b8; font-size: 0.8rem; font-style: italic; margin-bottom: 8px; line-height: 1.3;'><b>Evidence:</b> \"{iss.evidence_text or 'N/A'}\"</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    if st.button("✅ Confirm", key=f"top_conf_{iss.id}_{idx}", type="primary" if is_conf else "secondary", use_container_width=True):
                        db.update_reviewer_decision(iss.id, "Confirmed")
                        iss.reviewer_decision = "Confirmed"
                        st.rerun()
                with c_btn2:
                    if st.button("❌ Dismiss", key=f"top_dism_{iss.id}_{idx}", use_container_width=True):
                        db.update_reviewer_decision(iss.id, "Dismissed")
                        iss.reviewer_decision = "Dismissed"
                        st.rerun()

    # 3. Filters: severity (High / Medium / Low / All), status (Open / Resolved / All), category
    st.divider()
    st.markdown("### 🔍 Filters")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filter_sev = st.selectbox("Severity:", ["All", "High", "Medium", "Low"], key="prio_filter_sev")
    with col_f2:
        filter_status = st.selectbox("Status:", ["All", "Open", "Resolved"], key="prio_filter_status")
    with col_f3:
        all_categories = ["All"] + sorted(list(set(i.category for i in result.issues if i.category)))
        filter_cat = st.selectbox("Category:", all_categories, key="prio_filter_cat")

    filtered_issues = []
    for iss in result.issues:
        if filter_sev != "All" and iss.severity != filter_sev:
            continue
        if filter_status == "Open" and iss.status not in ("Open", "Still Open"):
            continue
        if filter_status == "Resolved" and iss.status != "Resolved":
            continue
        if filter_cat != "All" and iss.category != filter_cat:
            continue
        filtered_issues.append(iss)

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
                sev_border = "#dc2626" if iss.severity == "High" else ("#ea580c" if iss.severity == "Medium" else "#16a34a")
                sev_bg = "rgba(127, 29, 29, 0.12)" if iss.severity == "High" else ("rgba(124, 45, 18, 0.12)" if iss.severity == "Medium" else "rgba(20, 83, 45, 0.12)")
                card_style = f"border-left: 5px solid {sev_border}; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155; background-color: {sev_bg}; border-radius: 8px; padding: 12px; margin-bottom: 10px;"

            with st.container():
                st.markdown(f"<div style='{card_style}'>", unsafe_allow_html=True)
                c_left, c_mid, c_right = st.columns([1.5, 5, 2])
                with c_left:
                    st.markdown(f"**Issue #{idx + 1}**")
                    sev_color = "red" if iss.severity == "High" else ("orange" if iss.severity == "Medium" else "green")
                    st.markdown(f":{sev_color}[**{iss.severity} Severity**]")
                    st.caption(f"`{iss.category}`")
                    st.caption(f"Ref: {iss.evidence_page or 'N/A'}")
                    if is_dismissed:
                        st.markdown("<span style='color: #94a3b8; font-weight: bold;'>🚫 Dismissed<br><small>(Excluded from PDF)</small></span>", unsafe_allow_html=True)
                    elif is_confirmed:
                        st.markdown("<span style='color: #4ade80; font-weight: bold;'>✅ Confirmed</span>", unsafe_allow_html=True)
                    else:
                        st.markdown("<span style='color: #60a5fa;'>⏳ Pending</span>", unsafe_allow_html=True)

                with c_mid:
                    desc_color = "#94a3b8" if is_dismissed else "#f8fafc"
                    st.markdown(f"<p style='color: {desc_color}; margin: 0 0 4px 0;'><b>Description:</b> {iss.description}</p>", unsafe_allow_html=True)
                    if iss.evidence_text:
                        st.markdown(f"<p style='color: #94a3b8; font-size: 0.85rem; margin: 0 0 4px 0;'><b>Evidence Quote:</b> <i>\"{iss.evidence_text}\"</i></p>", unsafe_allow_html=True)
                    if iss.follow_up_question:
                        st.markdown(f"<p style='color: #cbd5e1; font-size: 0.85rem; margin: 0 0 4px 0;'><b>Applicant Query:</b> {iss.follow_up_question}</p>", unsafe_allow_html=True)
                    if iss.applicant_reply:
                        st.markdown(f"<p style='color: #67e8f9; font-size: 0.85rem; margin: 0;'><b>Applicant Reply:</b> <i>\"{iss.applicant_reply}\"</i></p>", unsafe_allow_html=True)

                with c_right:
                    st.caption("Reviewer Action:")
                    if st.button("✅ Confirm", key=f"prio_conf_{iss.id}_{idx}", use_container_width=True, type="primary" if is_confirmed else "secondary"):
                        db.update_reviewer_decision(iss.id, "Confirmed")
                        iss.reviewer_decision = "Confirmed"
                        st.rerun()
                    if st.button("❌ Dismiss", key=f"prio_dism_{iss.id}_{idx}", use_container_width=True):
                        db.update_reviewer_decision(iss.id, "Dismissed")
                        iss.reviewer_decision = "Dismissed"
                        st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)

    # Download updated report
    st.divider()
    c_dl1, c_dl2 = st.columns([1, 1])
    with c_dl1:
        pdf_bytes = report.generate_review_pdf(result)
        safe_filename = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in result.project_name.strip()).strip("_") or "EC_Report"
        st.download_button(
            label="📥 Download Updated Error Report (PDF)",
            data=pdf_bytes,
            file_name=f"VYRO_Review_Report_{safe_filename}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
            help="Download formal Review Report with dismissed issues excluded."
        )
    with c_dl2:
        if st.button("📊 View Full Audit Results & Clarification Loop", key="btn_return_results_bottom", use_container_width=True):
            st.session_state["auth_page"] = "results"
            st.rerun()

else:
    # --------------------------------------------------------------------------
    # PAGE 2: AUDIT RESULTS DASHBOARD & APPLICANT FOLLOW-UP (Dedicated Page)
    # --------------------------------------------------------------------------
    result: ReviewResult = st.session_state["review_result"]
    result.issues = db.sync_review_issues(result.project_name, result.issues)

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
    
    # 1. Metric: Completeness Score & Counts
    m1, m2, m3 = st.columns(3)
    with m1:
        score = result.completeness_score
        if score >= 80:
            delta_label = "High Compliance"
        elif score >= 50:
            delta_label = "Moderate Gaps"
        else:
            delta_label = "Critical Deficiencies"
        st.metric(label="Completeness Score", value=f"{score}%", delta=delta_label)
    with m2:
        st.metric(label="Missing Mandatory Studies", value=f"{len(result.missing_studies)}")
    with m3:
        st.metric(label="Flagged Discrepancies & Contradictions", value=f"{len(result.issues)}")

    # 2. Executive Summary
    st.markdown("### 📋 Executive Summary")
    st.info(result.summary)

    # 3. Missing Studies Section
    st.markdown("### 🚨 Missing Mandatory Studies")
    if result.missing_studies:
        cols = st.columns(min(max(len(result.missing_studies), 1), 3))
        for idx, study in enumerate(result.missing_studies):
            cols[idx % 3].error(f"❌ **Missing:** {study.title()}")
    else:
        st.success("✅ All mandatory checklist studies are addressed in the application.")

    # 4. Color-coded Issues Table (Pandas)
    st.markdown("### 🔍 Issues, Figures Inconsistencies & Contradictions")
    if result.issues:
        data = []
        for issue in result.issues:
            data.append({
                "Severity": issue.severity,
                "Category": issue.category,
                "Evidence Page": issue.evidence_page or "N/A",
                "Description": issue.description,
                "Evidence Quote": issue.evidence_text or "N/A",
                "Follow-up Query to Applicant": issue.follow_up_question or "N/A"
            })
        df = pd.DataFrame(data)

        # High red, Medium orange, Low green
        def color_severity(val):
            if val == "High":
                return "background-color: #7f1d1d; color: #fecaca; font-weight: bold;"
            elif val == "Medium":
                return "background-color: #7c2d12; color: #fed7aa; font-weight: bold;"
            elif val == "Low":
                return "background-color: #14532d; color: #bbf7d0; font-weight: bold;"
            return ""

        styled_df = df.style.map(color_severity, subset=["Severity"])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
    else:
        st.success("🎉 No internal discrepancies or contradictions found in the submitted report.")

    # 5. Export / Download Error Report (PDF)
    st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
    
    col_dl, col_reset = st.columns([1, 1])
    with col_dl:
        pdf_bytes = report.generate_review_pdf(result)
        safe_filename = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in result.project_name.strip()).strip("_")
        if not safe_filename:
            safe_filename = "EC_Report"

        st.download_button(
            label="📥 Download Error Report (PDF)",
            data=pdf_bytes,
            file_name=f"VYRO_Review_Report_{safe_filename}.pdf",
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
    total_issues = len(result.issues)
    resolved_issues = [i for i in result.issues if i.status == "Resolved"]
    unresolved_issues = [i for i in result.issues if i.status != "Resolved"]
    x_count = len(resolved_issues)
    y_count = total_issues

    progress_ratio = (x_count / y_count) if y_count > 0 else 1.0
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
                    sev_color = "red" if issue.severity == "High" else ("orange" if issue.severity == "Medium" else "green")
                    st.markdown(f"**Issue #{idx + 1}**")
                    st.markdown(f":{sev_color}[**{issue.severity} Severity**]")
                    st.caption(f"`{issue.category}`")
                    st.caption(f"Ref: {issue.evidence_page or 'N/A'}")
                    if issue.status == "Still Open":
                        st.badge("Still Open", color="red")
                    elif issue.status == "Needs More Info":
                        st.badge("Needs More Info", color="orange")
                    else:
                        st.badge("Open", color="blue")

                with col_meta:
                    st.markdown(f"**Description:** {issue.description}")
                    if issue.evidence_text:
                        st.markdown(f"**Evidence Cited:** *\"{issue.evidence_text}\"*")
                    
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
                            supporting_text = ""
                            if supporting_pdf is not None:
                                with st.spinner("📄 Extracting text from supporting PDF..."):
                                    pdf_text, _ = extract.extract_text(supporting_pdf)
                                    supporting_text = pdf_text or ""
                            
                            with st.spinner("🤖 Auditing reply with VYRO AI Compliance Engine..."):
                                followup_res = review.check_followup(issue, reply_input, supporting_text)
                            
                            # Update in DB
                            db.update_issue_followup(
                                issue_id=issue.id,
                                status=followup_res.status,
                                applicant_reply=reply_input.strip(),
                                ai_reason=followup_res.reason
                            )
                            # Update in memory
                            issue.status = followup_res.status
                            issue.applicant_reply = reply_input.strip()
                            issue.ai_reason = followup_res.reason

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

