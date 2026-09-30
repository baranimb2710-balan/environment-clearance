"""
Verification script for the new services.py layer.
Verifies all 12 services functions and the complete
upload -> review -> priority triage -> report flow.
"""
import os
import sys
import io

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import services
from models import Issue, ReviewResult

def test_services():
    print("--- 1. Testing Database & Auth Services ---")
    services.init_database()
    auth = services.get_authenticator()
    assert auth is not None
    print("PASS: get_authenticator()")

    import random
    suffix = random.randint(10000, 99999)
    ok, msg = services.register_user(
        name=f"Service User {suffix}",
        username=f"svc_user_{suffix}",
        email=f"svc_{suffix}@example.com",
        password="password123",
        confirm_password="password123",
        role="applicant"
    )
    assert ok is True
    print(f"PASS: register_user() -> {msg}")

    user = services.get_user_profile(f"svc_user_{suffix}")
    assert user is not None
    assert user["username"] == f"svc_user_{suffix}"
    print("PASS: get_user_profile()")

    print("\n--- 2. Testing Application Review Flow ---")
    pdf_path = r"c:\EC app\sample_ec_report.pdf"
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    trace_log = []
    def dummy_trace(step):
        trace_log.append(step)

    test_project = f"Services Test Project {suffix}"
    review_res, err, pages = services.process_application_review(
        uploaded_file=pdf_bytes,
        project_name=test_project,
        trace_callback=dummy_trace
    )
    assert err is None
    assert review_res is not None
    assert review_res.completeness_score > 0
    assert len(review_res.issues) > 0
    print(f"PASS: process_application_review() -> Score: {review_res.completeness_score}%, Issues: {len(review_res.issues)}, Trace: {len(trace_log)} steps")

    print("\n--- 3. Testing Audit Loading & Sync ---")
    loaded = services.load_project_audit(test_project)
    assert loaded is not None
    assert loaded.project_name == test_project
    assert len(loaded.issues) == len(review_res.issues)
    print("PASS: load_project_audit()")

    print("\n--- 4. Testing Reviewer Priority Functions ---")
    metrics = services.calculate_reviewer_metrics(review_res.issues)
    assert metrics["total"] == len(review_res.issues)
    assert "high" in metrics and "open" in metrics
    print(f"PASS: calculate_reviewer_metrics() -> {metrics}")

    top_3 = services.get_top_critical_issues(review_res.issues, limit=3)
    assert len(top_3) <= 3
    print(f"PASS: get_top_critical_issues() -> Count: {len(top_3)}")

    first_iss = review_res.issues[0]
    ok_decision = services.update_issue_decision(first_iss, "Confirmed")
    assert ok_decision is True
    assert first_iss.reviewer_decision == "Confirmed"
    print("PASS: update_issue_decision(Confirmed)")

    filtered = services.filter_issues(review_res.issues, severity="All", status="All", category="All")
    assert len(filtered) == len(review_res.issues)
    print(f"PASS: filter_issues() -> Count: {len(filtered)}")

    print("\n--- 5. Testing Table Data Formatting & PDF Report Generation ---")
    table_data = services.format_issues_table_data(review_res.issues)
    assert len(table_data) == len(review_res.issues)
    assert "Severity" in table_data[0]
    print(f"PASS: format_issues_table_data() -> {len(table_data)} rows")

    pdf_bytes, filename = services.generate_report_download(review_res)
    assert pdf_bytes.startswith(b"%PDF")
    assert filename.endswith(".pdf")
    print(f"PASS: generate_report_download() -> File: {filename}, Size: {len(pdf_bytes)} bytes")

    print("\n--- 6. Testing Applicant Follow-up Loop ---")
    x, y, ratio, res_iss, unres_iss = services.calculate_resolution_progress(review_res.issues)
    assert y == len(review_res.issues)
    print(f"PASS: calculate_resolution_progress() -> {x}/{y} resolved (ratio: {ratio:.2f})")

    followup_res, db_ok = services.submit_applicant_followup(
        issue=first_iss,
        reply_text="We have installed high-efficiency wet scrubbers with 99.5% efficiency and updated the water balance.",
        supporting_pdf=None
    )
    assert followup_res is not None
    assert db_ok is True
    print(f"PASS: submit_applicant_followup() -> Status: {followup_res.status}")

    print("\n==========================================")
    print("SUCCESS: ALL SERVICES LAYER CHECKS PASSED!")
    print("==========================================")

if __name__ == "__main__":
    test_services()
