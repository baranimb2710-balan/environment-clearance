"""
Service layer for VYRO - Environmental Clearance Application Review System.
Centralizes all business logic, scoring algorithms, filtering rules, database operations,
data transformations, and pipeline orchestrations outside of the Streamlit UI.
"""
import json
from typing import Optional, List, Dict, Any, Tuple, Callable
import streamlit_authenticator as stauth

import db
import extract
import review
import report
from models import Issue, ReviewResult, FollowupResult, UserRole, RuleEvaluation
from scoring import calculate_readiness


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


def record_user_login(username: str) -> bool:
    """Updates the last_login timestamp in users table upon authentication."""
    return db.update_user_last_login(username)


def get_users_page_data() -> List[Dict[str, Any]]:
    """Retrieves user accounts strictly for the Users view (email, signup date, last login)."""
    return db.get_users_view()


def get_reports_page_data(username: Optional[str] = None, role: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves application and report records strictly for the Reports view."""
    return db.get_reports_view(username=username, role=role)


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
    Issue models with evidence quotes and reviewer actions, preserves completeness score,
    and sorts issues by severity then confidence.
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
            severity=r.get("severity") or "Major",
            confidence=r.get("confidence") or "Medium",
            description=r["description"] or "",
            page_number=r.get("page_number") or r.get("evidence_page"),
            quote=r.get("quote") or r.get("evidence_text"),
            evidence_page=r.get("evidence_page") or r.get("page_number"),
            evidence_text=r.get("evidence_text") or r.get("quote"),
            follow_up_question=r["follow_up_question"],
            status=r["status"] or "Open",
            applicant_reply=r["applicant_reply"],
            ai_reason=r["ai_reason"],
            reviewer_decision=r.get("reviewer_decision", "Pending") or "Pending",
            reviewer_comment=r.get("reviewer_comment"),
            reviewed_at=str(r["reviewed_at"]) if r.get("reviewed_at") else None
        )
        loaded_issues.append(iss)
        if iss.category == "Missing Study":
            clean_m = iss.description.replace("Missing mandatory study: ", "").strip()
            if clean_m and clean_m not in missing_st:
                missing_st.append(clean_m)

    # Fetch stored score, summary, missing_studies, and rule_results from applications table
    stored_score = None
    stored_summary = None
    stored_missing = None
    stored_rules: List[RuleEvaluation] = []
    with db.db_session() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT completeness_score, summary, missing_studies,
                   readiness_score, readiness_band, readiness_range_low,
                   readiness_range_high, rule_results
            FROM applications WHERE project_name = ?
            """,
            (clean_pname,)
        )
        app_row = cur.fetchone()
        if app_row:
            stored_score = app_row["completeness_score"]
            stored_summary = app_row["summary"]
            if app_row["missing_studies"]:
                try:
                    parsed = json.loads(app_row["missing_studies"])
                    if isinstance(parsed, list):
                        stored_missing = parsed
                except Exception:
                    stored_missing = None
            if app_row["rule_results"]:
                try:
                    raw_r = json.loads(app_row["rule_results"])
                    if isinstance(raw_r, list):
                        stored_rules = [RuleEvaluation(**r) for r in raw_r]
                except Exception:
                    stored_rules = []

    if stored_score is not None:
        final_score = stored_score
    else:
        resolved_count = sum(1 for i in loaded_issues if i.status == "Resolved")
        final_score = min(
            95,
            max(30, int((len(loaded_issues) - (len(loaded_issues) - resolved_count)) / max(len(loaded_issues), 1) * 100))
        )

    final_missing = stored_missing if stored_missing is not None else missing_st
    stored_trace = db.get_application_trace(clean_pname)
    final_summary = stored_summary or f"Audit loaded from database for '{clean_pname}'. Contains {len(loaded_issues)} tracked compliance issues."

    # Sort issues by severity then confidence
    sorted_issues = sort_issues_by_priority(loaded_issues)

    # Calculate statutory readiness score
    readiness_data = calculate_readiness(stored_rules, sorted_issues)

    return ReviewResult(
        project_name=clean_pname,
        completeness_score=final_score,
        missing_studies=final_missing,
        issues=sorted_issues,
        summary=final_summary,
        agent_trace=stored_trace,
        rule_results=stored_rules,
        readiness_score=readiness_data["score"],
        readiness_band=readiness_data["band"],
        readiness_range_low=readiness_data["range_low"],
        readiness_range_high=readiness_data["range_high"],
        readiness_category_counts=readiness_data["category_counts"],
        readiness_improvements=readiness_data["top_improvements"]
    )


# ------------------------------------------------------------------------------
# 3. Application Review Pipeline Orchestration (Live 5-Step Progress)
# ------------------------------------------------------------------------------
def sort_issues_by_priority(issues: List[Issue]) -> List[Issue]:
    """
    Sorts issues primarily by severity (Critical > Major > Minor),
    and secondarily by confidence (High > Medium > Low).
    """
    sev_rank = {"Critical": 0, "High": 0, "Major": 1, "Medium": 1, "Minor": 2, "Low": 2}
    conf_rank = {"High": 0, "Medium": 1, "Low": 2}
    return sorted(issues, key=lambda i: (sev_rank.get(i.severity, 1), conf_rank.get(i.confidence, 1)))


def process_application_review(
    uploaded_file: Any,
    project_name: str,
    trace_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    progress_callback: Optional[Callable[[str, str, Dict[str, Any]], None]] = None,
    owner_username: Optional[str] = None
) -> Tuple[Optional[ReviewResult], Optional[str], Optional[int]]:
    """
    Extracts text from PDF, executes the multi-agent review pipeline,
    persists results to SQLite, and synchronizes issues.
    Reports progress for 5 distinct stages: Extracting text, Planner, Specialists, Verifier, Saving.
    Returns: (ReviewResult, error_message, total_pages)
    """
    clean_pname = project_name.strip()
    if not clean_pname:
        return None, "Please enter a valid Project Name before submitting.", None
    if uploaded_file is None:
        return None, "Please upload a PDF file of the Environmental Clearance report.", None

    # Step 1: Extracting text
    if progress_callback:
        progress_callback("Extracting text", "start", {"message": "Extracting digital text page-by-page from PDF..."})
    extracted_text, total_pages = extract.extract_text(uploaded_file)
    if not extracted_text:
        if progress_callback:
            progress_callback("Extracting text", "error", {"message": "Scanned or image-only PDF detected"})
        return (
            None,
            "⚠️ **Scanned or Image-Only PDF Detected:** The uploaded document contains no extractable digital text. Per system guidelines, OCR is disabled. Please upload a report containing digital selectable text.",
            total_pages
        )
    if progress_callback:
        progress_callback("Extracting text", "complete", {"pages": total_pages})

    # Steps 2-4: Planner, Specialists, Verifier
    try:
        review_result = review.review_application(
            extracted_text,
            project_name=clean_pname,
            trace_callback=trace_callback,
            progress_callback=progress_callback
        )

        # Step 5: Saving
        if progress_callback:
            progress_callback("Saving", "start", {"message": "Storing audit trace, missing studies, and issues in database..."})
        db.store_application_trace(
            project_name=clean_pname,
            agent_trace=review_result.agent_trace,
            completeness_score=review_result.completeness_score,
            summary=review_result.summary,
            owner_username=owner_username,
            missing_studies=review_result.missing_studies,
            readiness_score=review_result.readiness_score,
            readiness_band=review_result.readiness_band,
            readiness_range_low=review_result.readiness_range_low,
            readiness_range_high=review_result.readiness_range_high,
            rule_results=review_result.rule_results
        )
        # Synchronize issues with followups table
        review_result.issues = db.sync_review_issues(clean_pname, review_result.issues)
        # Sort issues by severity then confidence
        review_result.issues = sort_issues_by_priority(review_result.issues)
        if progress_callback:
            progress_callback("Saving", "complete", {"issues_count": len(review_result.issues)})

        return review_result, None, total_pages
    except Exception as e:
        if progress_callback:
            progress_callback("Review Pipeline", "error", {"message": str(e)})
        return None, f"Review error: {str(e)}", total_pages


# ------------------------------------------------------------------------------
# 4. Reviewer Priority View Metrics, Sorting & Filtering
# ------------------------------------------------------------------------------
def calculate_reviewer_metrics(issues: List[Issue]) -> Dict[str, int]:
    """Calculates summary metric counts for reviewer priority triage."""
    confirmed = sum(1 for i in issues if getattr(i, "reviewer_decision", None) == "Confirmed")
    dismissed = sum(1 for i in issues if getattr(i, "reviewer_decision", None) == "Dismissed")
    pending = len(issues) - confirmed - dismissed
    return {
        "total": len(issues),
        "critical": sum(1 for i in issues if i.severity in ("Critical", "High")),
        "high": sum(1 for i in issues if i.severity in ("Critical", "High")),
        "major": sum(1 for i in issues if i.severity in ("Major", "Medium")),
        "minor": sum(1 for i in issues if i.severity in ("Minor", "Low")),
        "open": sum(1 for i in issues if i.status in ("Open", "Still Open")),
        "confirmed": confirmed,
        "dismissed": dismissed,
        "pending": max(0, pending)
    }


def get_reviewer_action_counts(issues: List[Issue]) -> Dict[str, int]:
    """Returns counts of confirmed, dismissed, and pending issues."""
    confirmed = sum(1 for i in issues if getattr(i, "reviewer_decision", None) == "Confirmed")
    dismissed = sum(1 for i in issues if getattr(i, "reviewer_decision", None) == "Dismissed")
    pending = len(issues) - confirmed - dismissed
    return {
        "confirmed": confirmed,
        "dismissed": dismissed,
        "pending": max(0, pending),
        "total": len(issues)
    }


def get_top_critical_issues(issues: List[Issue], limit: int = 3) -> List[Issue]:
    """
    Ranks issues by Critical severity first, then Open status, then Contradiction category.
    Prioritizes active/un-dismissed issues and returns the top `limit`.
    """
    def priority_sort_key(iss: Issue) -> Tuple[int, int, int]:
        sev_rank = {"Critical": 0, "High": 0, "Major": 1, "Medium": 1, "Minor": 2, "Low": 2}.get(iss.severity, 3)
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
        if severity != "All":
            if severity == "Critical" and iss.severity not in ("Critical", "High"):
                continue
            elif severity == "Major" and iss.severity not in ("Major", "Medium"):
                continue
            elif severity == "Minor" and iss.severity not in ("Minor", "Low"):
                continue
            elif severity not in ("Critical", "Major", "Minor") and iss.severity != severity:
                continue
        if status == "Open" and iss.status not in ("Open", "Still Open"):
            continue
        if status == "Resolved" and iss.status != "Resolved":
            continue
        if category != "All" and iss.category != category:
            continue
        filtered.append(iss)
    return filtered


def refresh_review_readiness(result: Optional[ReviewResult]) -> Optional[ReviewResult]:
    """
    Recalculates Clearance Readiness Score, band, bounds, and improvements on a ReviewResult model.
    Defensively falls back to SQLite application records if rule_results are not yet populated.
    """
    if result is None:
        return None

    rules = getattr(result, "rule_results", None) or []
    # If in-memory rules are empty, load from SQLite applications table if present
    if not rules and getattr(result, "project_name", None):
        app_rec = db.get_application_record(result.project_name)
        if app_rec and app_rec.get("rule_results"):
            try:
                raw_rules = json.loads(app_rec["rule_results"])
                rules = [RuleEvaluation(**r) if isinstance(r, dict) else r for r in raw_rules]
                result.rule_results = rules
            except Exception:
                pass

    readiness_data = calculate_readiness(rules, getattr(result, "issues", []) or [])
    result.readiness_score = readiness_data["score"]
    result.readiness_band = readiness_data["band"]
    result.readiness_range_low = readiness_data["range_low"]
    result.readiness_range_high = readiness_data["range_high"]
    result.readiness_category_counts = readiness_data["category_counts"]
    result.readiness_improvements = readiness_data["top_improvements"]
    return result


def save_reviewer_action(
    issue: Issue,
    decision: str,
    comment: Optional[str] = None,
    result: Optional[ReviewResult] = None
) -> bool:
    """
    Updates reviewer_decision and optional reviewer_comment in SQLite and mutates in-memory model.
    Triggers automatic score recalculation in SQLite and on the ReviewResult session model if provided.
    """
    success = db.update_reviewer_action(issue.id, decision, comment)
    if success:
        issue.reviewer_decision = decision
        if comment:
            issue.reviewer_comment = comment
        if result is not None:
            refresh_review_readiness(result)
    return success


def update_issue_decision(issue: Issue, decision: str) -> bool:
    """Updates reviewer_decision for an issue in SQLite and mutates in-memory model."""
    return save_reviewer_action(issue, decision, None)


# ------------------------------------------------------------------------------
# 5. Data Shaping & Reporting Services
# ------------------------------------------------------------------------------
def format_issues_table_data(issues: List[Issue]) -> List[Dict[str, Any]]:
    """Transforms Issue models into dictionary format for display in a Pandas DataFrame."""
    data = []
    for issue in sort_issues_by_priority(issues):
        data.append({
            "Severity": issue.severity,
            "Confidence": issue.confidence,
            "Category": issue.category,
            "Page": issue.page_number or issue.evidence_page or "N/A",
            "Exact Quote (<=25 words)": issue.quote or issue.evidence_text or "N/A",
            "Description": issue.description,
            "Reviewer Status": issue.reviewer_decision or "Pending",
            "Reviewer Comment": issue.reviewer_comment or "-"
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
