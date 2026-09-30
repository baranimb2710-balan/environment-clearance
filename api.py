"""
FastAPI REST API for VYRO Environmental Clearance Application Reviewer.
Exposes existing authentication, application review, issue decision, and report generation services.
"""
import os
import json
import sqlite3
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status, Body, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Load environment variables (.env)
load_dotenv()

# Existing modules (no logic rewritten or moved)
import db
import extract
import review
import report
from models import UserCreate, Issue, ReviewResult
from agents.tools import EC_CHECKLIST

# Initialize database schema if not present
db.init_db()

# Create FastAPI application
app = FastAPI(
    title="VYRO Environmental Clearance API",
    description="REST API for automated EIA/EMP report review, multi-agent compliance auditing, applicant clarifications, and PDF reporting.",
    version="1.0.0"
)

# Enable Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------------------
# Request Schemas
# ------------------------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, description="Username or email")
    password: str = Field(..., min_length=1, description="Account password")


class IssueStatusRequest(BaseModel):
    status: Optional[str] = Field(None, description="'Confirm' or 'Dismiss'")
    decision: Optional[str] = Field(None, description="'Confirm' or 'Dismiss'")


# ------------------------------------------------------------------------------
# Database Helpers for API Layer
# ------------------------------------------------------------------------------
def find_application(app_identifier: str) -> Optional[Dict[str, Any]]:
    """Lookup application record by integer rowid or project_name."""
    clean_id = app_identifier.strip()
    with db.get_db_connection() as conn:
        cur = conn.cursor()
        if clean_id.isdigit():
            cur.execute(
                "SELECT rowid AS id, * FROM applications WHERE rowid = ? OR project_name = ?",
                (int(clean_id), clean_id)
            )
        else:
            cur.execute(
                "SELECT rowid AS id, * FROM applications WHERE project_name = ?",
                (clean_id,)
            )
        row = cur.fetchone()
        if row:
            return dict(row)
    return None


# ------------------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------------------

@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint to verify API service status."""
    return {
        "status": "healthy",
        "service": "VYRO Environmental Clearance API",
        "version": "1.0.0"
    }


# 1. Authentication Endpoints
@app.post("/auth/signup", status_code=status.HTTP_201_CREATED, tags=["Authentication"])
def signup(user: UserCreate):
    """
    Registers a new user account (role: 'reviewer' or 'applicant').
    Uses existing db.py logic and bcrypt hashing.
    """
    success, message = db.create_user(
        username=user.username,
        name=user.name,
        email=user.email,
        plain_password=user.password,
        role=user.role
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    return {
        "message": message,
        "user": {
            "username": user.username,
            "name": user.name,
            "email": user.email,
            "role": user.role
        }
    }


@app.post("/auth/login", tags=["Authentication"])
def login(creds: LoginRequest):
    """
    Authenticates user credentials using bcrypt and returns user profile.
    """
    user = db.get_user(creds.username)
    if not user or not db.verify_password(creds.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    return {
        "message": "Login successful",
        "user": {
            "username": user["username"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
    }


# 2. Application Audit & Review (Multipart PDF)
@app.post("/applications", status_code=status.HTTP_201_CREATED, tags=["Applications"])
async def create_application_review(
    file: UploadFile = File(..., description="Environmental Clearance Application PDF"),
    project_name: str = Form(..., description="Official project or plant name")
):
    """
    Uploads an EC application PDF and project name.
    1. Extracts digital text page-by-page via extract.py (PyMuPDF).
    2. Runs Multi-Agent Review Pipeline (review.review_application()).
    3. Persists trace and issues to SQLite.
    4. Returns score, rule_results, and issues.
    """
    clean_pname = project_name.strip()
    if not clean_pname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project name cannot be empty."
        )

    filename = (file.filename or "").lower()
    if not filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF documents are supported."
        )

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    # Step 1: Text extraction
    extracted_text, total_pages = extract.extract_text(pdf_bytes)
    if not extracted_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded document contains no extractable digital text (scanned or image-only PDF). Selectable digital text is required."
        )

    # Step 2: Multi-agent audit pipeline
    try:
        review_result = review.review_application(extracted_text, project_name=clean_pname)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Review pipeline execution error: {str(err)}"
        )

    # Step 3: Persist trace in applications table & sync issues in followups table
    db.store_application_trace(
        project_name=clean_pname,
        agent_trace=review_result.agent_trace,
        completeness_score=review_result.completeness_score,
        summary=review_result.summary
    )
    synced_issues = db.sync_review_issues(clean_pname, review_result.issues)
    review_result.issues = synced_issues

    # Retrieve rowid for response
    app_record = find_application(clean_pname)
    app_id = app_record["id"] if app_record else None

    # Construct rule_results
    rule_results = {
        "missing_studies": review_result.missing_studies,
        "checklist": [
            {
                "study": study,
                "status": "Missing" if study in review_result.missing_studies else "Passed"
            }
            for study in EC_CHECKLIST
        ],
        "summary": review_result.summary
    }

    return {
        "id": app_id,
        "project_name": review_result.project_name,
        "score": review_result.completeness_score,
        "rule_results": rule_results,
        "issues": [issue.model_dump() for issue in review_result.issues]
    }


# 3. List and Get Application Details
@app.get("/applications", tags=["Applications"])
def list_applications():
    """
    Lists all reviewed applications with summary metrics.
    """
    with db.get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT rowid AS id, project_name, completeness_score, summary, updated_at 
            FROM applications 
            ORDER BY updated_at DESC
            """
        )
        rows = cur.fetchall()

    results = []
    for r in rows:
        followups = db.get_project_followups(r["project_name"])
        total_issues = len(followups)
        open_issues = sum(1 for i in followups if i.get("status") in ("Open", "Still Open"))
        results.append({
            "id": r["id"],
            "project_name": r["project_name"],
            "score": r["completeness_score"],
            "summary": r["summary"],
            "total_issues": total_issues,
            "open_issues": open_issues,
            "updated_at": r["updated_at"]
        })
    return results


@app.get("/applications/{id}", tags=["Applications"])
def get_application(id: str):
    """
    Retrieves full details of an application (by ID or project name),
    including all tracked issues and the multi-agent execution trace.
    """
    app_record = find_application(id)
    if not app_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{id}' not found."
        )

    pname = app_record["project_name"]
    issues = db.get_project_followups(pname)
    agent_trace = []
    if app_record.get("agent_trace"):
        try:
            agent_trace = json.loads(app_record["agent_trace"])
        except Exception:
            pass

    return {
        "id": app_record["id"],
        "project_name": pname,
        "score": app_record["completeness_score"],
        "summary": app_record["summary"],
        "updated_at": app_record["updated_at"],
        "issues": issues,
        "agent_trace": agent_trace
    }


# 4. Reviewer Decision on Issue (Confirm / Dismiss)
@app.post("/applications/{id}/issues/{issue_id}/status", tags=["Applications"])
def update_issue_status(
    id: str,
    issue_id: str,
    payload: IssueStatusRequest = Body(...)
):
    """
    Updates the reviewer decision for a specific issue ('Confirm' or 'Dismiss').
    Persists decision in SQLite followups table.
    """
    app_record = find_application(id)
    if not app_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{id}' not found."
        )

    # Determine desired status / decision
    raw_status = (payload.decision or payload.status or "").strip().lower()
    if raw_status in ("confirm", "confirmed"):
        decision = "Confirmed"
    elif raw_status in ("dismiss", "dismissed"):
        decision = "Dismissed"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status/decision must be either 'Confirm' or 'Dismiss'."
        )

    # Verify issue belongs to this project
    pname = app_record["project_name"]
    with db.get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT issue_id FROM followups WHERE issue_id = ? AND project_name = ?",
            (issue_id.strip(), pname)
        )
        if not cur.fetchone():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Issue '{issue_id}' not found for application '{pname}'."
            )

    success = db.update_reviewer_decision(issue_id.strip(), decision)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update issue reviewer decision in database."
        )

    return {
        "message": f"Issue reviewer decision updated to {decision}",
        "issue_id": issue_id,
        "reviewer_decision": decision
    }


# 5. Download Review PDF Report
@app.get("/applications/{id}/report", tags=["Applications"])
def download_application_report(id: str):
    """
    Generates and returns the PDF Review Report for the application
    using ReportLab (report.py). Excludes dismissed issues automatically.
    """
    app_record = find_application(id)
    if not app_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Application '{id}' not found."
        )

    pname = app_record["project_name"]
    records = db.get_project_followups(pname)

    # Reconstruct Issue objects
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

    review_res = ReviewResult(
        project_name=pname,
        completeness_score=app_record.get("completeness_score") or 0,
        missing_studies=missing_st,
        issues=loaded_issues,
        summary=app_record.get("summary") or f"Environmental clearance report audit for {pname}."
    )

    pdf_bytes = report.generate_review_pdf(review_res)

    safe_filename = "".join(c for c in pname if c.isalnum() or c in (" ", "-", "_")).strip().replace(" ", "_")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}_Review_Report.pdf"'
        }
    )
