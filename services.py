"""
Service layer for VYRO - Environmental Clearance Application Review System.
Centralizes all business logic, scoring algorithms, filtering rules, database operations,
data transformations, and pipeline orchestrations outside of the Streamlit UI.
"""
from typing import Optional, List, Dict, Any, Tuple, Callable
import streamlit_authenticator as stauth

import db
import extract
import review
import report
from models import Issue, ReviewResult, FollowupResult, UserRole


# ------------------------------------------------------------------------------
# 1. Database & Authentication Services
# ------------------------------------------------------------------------------
def init_database() -> None:
    """Initializes SQLite database tables and seeds demo accounts."""
    db.init_db()


def get_authenticator() -> stauth.Authenticate:
    """
    Initializes and returns the Streamlit Authenticator instance
    using credentials loaded from SQLite.
    """
    credentials = db.get_authenticator_credentials()
    return stauth.Authenticate(
        credentials=credentials,
        cookie_name="ec_review_auth_cookie",
        cookie_key="ec_jwt_secret_token_key_review_app_2026",
        cookie_expiry_days=1.0,
        auto_hash=False  # Passwords are pre-hashed with bcrypt in SQLite
    )


def register_user(
    name: str,
    username: str,
    email: str,
    password: str,
    confirm_password: str,
    role: str
) -> Tuple[bool, str]:
    """
    Validates user registration input and creates the user in SQLite.
    Returns (success: bool, message: str).
    """
    if not name.strip() or not username.strip() or not email.strip():
        return False, "All fields are mandatory."
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
    if password != confirm_password:
        return False, "Passwords do not match."

    return db.create_user(
        username=username,
        name=name,
        email=email,
        plain_password=password,
        role=role
    )


def get_user_profile(username: str) -> Optional[Dict[str, Any]]:
    """Retrieves user account info from SQLite by username."""
    if not username:
        return None
    return db.get_user(username)


# ------------------------------------------------------------------------------
# 2. Audit History & Project Loading Services
# ------------------------------------------------------------------------------
def get_all_reviewed_projects(username: Optional[str] = None, role: Optional[str] = None) -> List[str]:
    """Returns list of all audited project names present in the database, filtered by user if applicant."""
    return db.get_all_projects_with_followups(username=username, role=role)


def sync_project_issues(project_name: str, issues: List[Issue]) -> List[Issue]:
    """Synchronizes in-memory issues with SQLite database."""
    return db.sync_review_issues(project_name, issues)


def load_project_audit(project_name: str) -> Optional[ReviewResult]:
    """
    Loads past audit issues and agent trace from SQLite, reconstitutes
    Issue models, preserves original completeness score, and builds ReviewResult.
    """
    clean_pname = project_name.strip()
    records = db.get_project_followups(clean_pname)
    if not records:
        return None

    loaded_issues: List[Issue] = []
    missing_st: List[str] = []

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

    # Fetch stored score and summary from applications table
    stored_score = None
    stored_summary = None
    with db.db_session() as conn:
        cur = conn.cursor()
        cur.execute("SELECT completeness_score, summary FROM applications WHERE project_name = ?", (clean_pname,))
        app_row = cur.fetchone()
        if app_row:
            stored_score = app_row["completeness_score"]
            stored_summary = app_row["summary"]

    if stored_score is not None:
        final_score = stored_score
    else:
        resolved_count = sum(1 for i in loaded_issues if i.status == "Resolved")
        final_score = min(
            95,
            max(30, int((len(loaded_issues) - (len(loaded_issues) - resolved_count)) / max(len(loaded_issues), 1) * 100))
        )

    stored_trace = db.get_application_trace(clean_pname)
    final_summary = stored_summary or f"Audit loaded from database for '{clean_pname}'. Contains {len(loaded_issues)} tracked compliance issues."

    return ReviewResult(
        project_name=clean_pname,
        completeness_score=final_score,
        missing_studies=missing_st,
        issues=loaded_issues,
        summary=final_summary,
        agent_trace=stored_trace
    )


# ------------------------------------------------------------------------------
# 3. Application Review Pipeline Orchestration
# ------------------------------------------------------------------------------
def process_application_review(
    uploaded_file: Any,
    project_name: str,
    trace_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    owner_username: Optional[str] = None
) -> Tuple[Optional[ReviewResult], Optional[str], Optional[int]]:
    """
    Extracts text from PDF, executes the multi-agent review pipeline,
    persists results to SQLite, and synchronizes issues.
    Returns: (ReviewResult, error_message, total_pages)
    """
    clean_pname = project_name.strip()
    if not clean_pname:
        return None, "Please enter a valid Project Name before submitting.", None
    if uploaded_file is None:
        return None, "Please upload a PDF file of the Environmental Clearance report.", None

    # Step 1: Text extraction
    extracted_text, total_pages = extract.extract_text(uploaded_file)
    if not extracted_text:
        return (
            None,
            "⚠️ **Scanned or Image-Only PDF Detected:** The uploaded document contains no extractable digital text. Per system guidelines, OCR is disabled. Please upload a report containing digital selectable text.",
            total_pages
        )

    # Step 2: Multi-agent pipeline execution
    try:
        review_result = review.review_application(
            extracted_text,
            project_name=clean_pname,
            trace_callback=trace_callback
        )
        # Store execution trace and metadata in SQLite applications table
        db.store_application_trace(
            project_name=clean_pname,
            agent_trace=review_result.agent_trace,
            completeness_score=review_result.completeness_score,
            summary=review_result.summary,
            owner_username=owner_username
        )
        # Synchronize issues with followups table
        review_result.issues = db.sync_review_issues(clean_pname, review_result.issues)
        return review_result, None, total_pages
    except Exception as e:
        return None, f"Review error: {str(e)}", total_pages


# ------------------------------------------------------------------------------
# 4. Reviewer Priority View Metrics, Sorting & Filtering
# ------------------------------------------------------------------------------
def calculate_reviewer_metrics(issues: List[Issue]) -> Dict[str, int]:
    """Calculates summary metric counts for reviewer priority triage."""
    return {
        "total": len(issues),
        "high": sum(1 for i in issues if i.severity == "High"),
        "open": sum(1 for i in issues if i.status in ("Open", "Still Open")),
        "confirmed": sum(1 for i in issues if getattr(i, "reviewer_decision", None) == "Confirmed"),
        "dismissed": sum(1 for i in issues if getattr(i, "reviewer_decision", None) == "Dismissed")
    }


def get_top_critical_issues(issues: List[Issue], limit: int = 3) -> List[Issue]:
    """
    Ranks issues by High severity first, then Open status, then Contradiction category.
    Prioritizes active/un-dismissed issues and returns the top `limit`.
    """
    def priority_sort_key(iss: Issue) -> Tuple[int, int, int]:
        sev_rank = {"High": 0, "Medium": 1, "Low": 2}.get(iss.severity, 3)
        status_rank = 0 if iss.status in ("Open", "Still Open") else (1 if iss.status == "Needs More Info" else 2)
        cat_rank = 0 if iss.category == "Contradiction" else (1 if iss.category == "Inconsistency" else 2)
        return (sev_rank, status_rank, cat_rank)

    active_critical = [i for i in issues if getattr(i, "reviewer_decision", None) != "Dismissed"]
    if not active_critical:
        active_critical = issues
    return sorted(active_critical, key=priority_sort_key)[:limit]


def filter_issues(
    issues: List[Issue],
    severity: str,
    status: str,
    category: str
) -> List[Issue]:
    """Filters issues by severity, resolution status, and category."""
    filtered = []
    for iss in issues:
        if severity != "All" and iss.severity != severity:
            continue
        if status == "Open" and iss.status not in ("Open", "Still Open"):
            continue
        if status == "Resolved" and iss.status != "Resolved":
            continue
        if category != "All" and iss.category != category:
            continue
        filtered.append(iss)
    return filtered


def update_issue_decision(issue: Issue, decision: str) -> bool:
    """Updates reviewer_decision for an issue in SQLite and mutates in-memory model."""
    success = db.update_reviewer_decision(issue.id, decision)
    if success:
        issue.reviewer_decision = decision
    return success


# ------------------------------------------------------------------------------
# 5. Data Shaping & Reporting Services
# ------------------------------------------------------------------------------
def format_issues_table_data(issues: List[Issue]) -> List[Dict[str, Any]]:
    """Transforms Issue models into dictionary format for display in a Pandas DataFrame."""
    data = []
    for issue in issues:
        data.append({
            "Severity": issue.severity,
            "Category": issue.category,
            "Evidence Page": issue.evidence_page or "N/A",
            "Description": issue.description,
            "Evidence Quote": issue.evidence_text or "N/A",
            "Follow-up Query to Applicant": issue.follow_up_question or "N/A"
        })
    return data


def generate_report_download(result: ReviewResult) -> Tuple[bytes, str]:
    """
    Generates PDF bytes via report.py and constructs a safe download filename.
    Returns (pdf_bytes, filename).
    """
    pdf_bytes = report.generate_review_pdf(result)
    safe_filename = "".join(
        c if c.isalnum() or c in ("-", "_") else "_" for c in result.project_name.strip()
    ).strip("_")
    if not safe_filename:
        safe_filename = "EC_Report"
    return pdf_bytes, f"VYRO_Review_Report_{safe_filename}.pdf"


# ------------------------------------------------------------------------------
# 6. Applicant Follow-Up Loop Services
# ------------------------------------------------------------------------------
def calculate_resolution_progress(
    issues: List[Issue]
) -> Tuple[int, int, float, List[Issue], List[Issue]]:
    """
    Calculates resolution progress metrics.
    Returns: (x_resolved, y_total, progress_ratio, resolved_issues, unresolved_issues)
    """
    total_issues = len(issues)
    resolved_issues = [i for i in issues if i.status == "Resolved"]
    unresolved_issues = [i for i in issues if i.status != "Resolved"]
    x_count = len(resolved_issues)
    y_count = total_issues
    progress_ratio = (x_count / y_count) if y_count > 0 else 1.0
    return x_count, y_count, progress_ratio, resolved_issues, unresolved_issues


def submit_applicant_followup(
    issue: Issue,
    reply_text: str,
    supporting_pdf: Optional[Any] = None
) -> Tuple[FollowupResult, bool]:
    """
    Extracts text from supporting PDF if provided, checks applicant followup
    with review engine, commits verdict to SQLite, and updates in-memory Issue.
    Returns: (FollowupResult, is_success)
    """
    supporting_text = ""
    if supporting_pdf is not None:
        pdf_text, _ = extract.extract_text(supporting_pdf)
        supporting_text = pdf_text or ""

    followup_res = review.check_followup(issue, reply_text, supporting_text)

    # Persist in SQLite followups table
    db_success = db.update_issue_followup(
        issue_id=issue.id,
        status=followup_res.status,
        applicant_reply=reply_text.strip(),
        ai_reason=followup_res.reason
    )

    # Update in-memory issue
    issue.status = followup_res.status
    issue.applicant_reply = reply_text.strip()
    issue.ai_reason = followup_res.reason

    return followup_res, db_success
