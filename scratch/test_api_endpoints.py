"""
Automated test suite for VYRO FastAPI endpoints.
Tests:
- GET /health
- POST /auth/login
- POST /auth/signup
- POST /applications (multipart PDF upload)
- GET /applications
- GET /applications/{id}
- POST /applications/{id}/issues/{issue_id}/status (Confirm / Dismiss)
- GET /applications/{id}/report (PDF download)
"""
import urllib.request
import urllib.parse
import json
import os
import io

BASE_URL = "http://127.0.0.1:8000"

def test_health():
    print("\n--- 1. Testing GET /health ---")
    req = urllib.request.Request(f"{BASE_URL}/health")
    with urllib.request.urlopen(req) as resp:
        status_code = resp.getcode()
        body = json.loads(resp.read().decode())
        print(f"Status Code: {status_code}")
        print(f"Response: {body}")
        assert status_code == 200
        assert body["status"] == "healthy"
        print("PASS: /health")

def test_auth_login():
    print("\n--- 2. Testing POST /auth/login ---")
    data = json.dumps({"username": "admin", "password": "admin123"}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/auth/login",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        status_code = resp.getcode()
        body = json.loads(resp.read().decode())
        print(f"Status Code: {status_code}")
        print(f"Response: {body}")
        assert status_code == 200
        assert body["user"]["role"] == "reviewer"
        print("PASS: /auth/login")

def test_auth_signup():
    print("\n--- 3. Testing POST /auth/signup ---")
    import random
    suffix = random.randint(1000, 9999)
    signup_data = {
        "username": f"testuser_{suffix}",
        "name": f"Test Applicant {suffix}",
        "email": f"applicant_{suffix}@ecapp.test",
        "password": "securepassword123",
        "role": "applicant"
    }
    data = json.dumps(signup_data).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/auth/signup",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        status_code = resp.getcode()
        body = json.loads(resp.read().decode())
        print(f"Status Code: {status_code}")
        print(f"Response: {body}")
        assert status_code == 201
        assert body["user"]["username"] == signup_data["username"]
        print("PASS: /auth/signup")

def test_upload_application():
    print("\n--- 4. Testing POST /applications (Multipart PDF Upload) ---")
    pdf_path = r"c:\EC app\sample_ec_report.pdf"
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Missing sample PDF at {pdf_path}")
    
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    project_name = "API GreenHorizon Test Project"
    
    # Construct multipart/form-data
    body = io.BytesIO()
    # Field: project_name
    body.write(f"--{boundary}\r\n".encode())
    body.write(b'Content-Disposition: form-data; name="project_name"\r\n\r\n')
    body.write(f"{project_name}\r\n".encode())
    
    # Field: file
    body.write(f"--{boundary}\r\n".encode())
    body.write(b'Content-Disposition: form-data; name="file"; filename="sample_ec_report.pdf"\r\n')
    body.write(b'Content-Type: application/pdf\r\n\r\n')
    body.write(pdf_bytes)
    body.write(b"\r\n")
    
    body.write(f"--{boundary}--\r\n".encode())
    
    payload = body.getvalue()
    req = urllib.request.Request(
        f"{BASE_URL}/applications",
        data=payload,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(payload))
        }
    )
    with urllib.request.urlopen(req) as resp:
        status_code = resp.getcode()
        resp_data = json.loads(resp.read().decode())
        print(f"Status Code: {status_code}")
        print(f"Project: {resp_data.get('project_name')}")
        print(f"Score: {resp_data.get('score')}")
        print(f"Issues detected: {len(resp_data.get('issues', []))}")
        print(f"Rule results keys: {list(resp_data.get('rule_results', {}).keys())}")
        assert status_code == 201
        assert "score" in resp_data
        assert "rule_results" in resp_data
        assert "issues" in resp_data
        assert len(resp_data["issues"]) > 0
        print("PASS: POST /applications")
        return resp_data

def test_get_applications(created_app):
    print("\n--- 5. Testing GET /applications & GET /applications/{id} ---")
    # List applications
    req = urllib.request.Request(f"{BASE_URL}/applications")
    with urllib.request.urlopen(req) as resp:
        status_code = resp.getcode()
        apps = json.loads(resp.read().decode())
        print(f"Status Code: {status_code}")
        print(f"Total Applications in DB: {len(apps)}")
        assert status_code == 200
        assert len(apps) > 0
        print("PASS: GET /applications")

    app_id = created_app["id"]
    print(f"\n--- 6. Testing GET /applications/{app_id} ---")
    req_single = urllib.request.Request(f"{BASE_URL}/applications/{app_id}")
    with urllib.request.urlopen(req_single) as resp:
        status_code = resp.getcode()
        app_detail = json.loads(resp.read().decode())
        print(f"Status Code: {status_code}")
        print(f"App Detail Project: {app_detail['project_name']}")
        print(f"Tracked Issues: {len(app_detail['issues'])}")
        assert status_code == 200
        assert app_detail["project_name"] == created_app["project_name"]
        print("PASS: GET /applications/{id}")

def test_update_issue_status(created_app):
    print("\n--- 7. Testing POST /applications/{id}/issues/{issue_id}/status ---")
    app_id = created_app["id"]
    issue = created_app["issues"][0]
    issue_id = issue["id"]
    print(f"Updating issue {issue_id} to 'Confirmed'...")
    
    data = json.dumps({"decision": "Confirmed"}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/applications/{app_id}/issues/{issue_id}/status",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        status_code = resp.getcode()
        body = json.loads(resp.read().decode())
        print(f"Status Code: {status_code}")
        print(f"Response: {body}")
        assert status_code == 200
        assert body["reviewer_decision"] == "Confirmed"
        print("PASS: POST issue status update (Confirmed)")

    # Also test Dismiss
    data_dismiss = json.dumps({"decision": "Dismiss"}).encode()
    req_dismiss = urllib.request.Request(
        f"{BASE_URL}/applications/{app_id}/issues/{issue_id}/status",
        data=data_dismiss,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_dismiss) as resp:
        status_code = resp.getcode()
        body = json.loads(resp.read().decode())
        assert status_code == 200
        assert body["reviewer_decision"] == "Dismissed"
        print("PASS: POST issue status update (Dismissed)")

def test_download_report(created_app):
    print("\n--- 8. Testing GET /applications/{id}/report ---")
    app_id = created_app["id"]
    req = urllib.request.Request(f"{BASE_URL}/applications/{app_id}/report")
    with urllib.request.urlopen(req) as resp:
        status_code = resp.getcode()
        content_type = resp.headers.get("Content-Type")
        pdf_bytes = resp.read()
        print(f"Status Code: {status_code}")
        print(f"Content-Type: {content_type}")
        print(f"Downloaded PDF size: {len(pdf_bytes)} bytes")
        assert status_code == 200
        assert content_type == "application/pdf"
        assert pdf_bytes.startswith(b"%PDF")
        print("PASS: GET /applications/{id}/report (Valid PDF)")

if __name__ == "__main__":
    test_health()
    test_auth_login()
    test_auth_signup()
    created_app = test_upload_application()
    test_get_applications(created_app)
    test_update_issue_status(created_app)
    test_download_report(created_app)
    print("\n==========================================")
    print("SUCCESS: ALL FASTAPI ENDPOINTS VERIFIED & PASSED!")
    print("==========================================")
