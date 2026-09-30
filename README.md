# VYRO — Environmental Clearance Application Reviewer

VYRO is an automated AI assistant and compliance auditing system for Environmental Clearance (EC) applications, EIA reports, and EMP documents.

---

## Features
- **Multi-Agent Review Pipeline**: Autonomous Planner, Completeness Specialist, Consistency Specialist, Contradiction Specialist, and Verifier Agent.
- **Applicant Follow-Up Loop**: Interactive clarification loop where applicants can reply to queries and submit supporting documentation.
- **Reviewer Priority View**: Role-gated triage dashboard highlighting top critical issues with Confirm/Dismiss controls.
- **PDF Report Generation**: Official Review Report PDF generated via ReportLab with automatic table cell wrapping, severity color coding, and decision tracking.
- **FastAPI REST Service**: Programmatic interface for signup/login, PDF audit submission, issue updates, and report download.

---

## Run the Streamlit Web Application
To run the interactive Streamlit UI:
```bash
streamlit run app.py
```
By default, the web interface is available at `http://localhost:8501`.

---

## Run the API
To start the FastAPI REST API server with auto-reload:
```bash
uvicorn api:app --reload
```
By default, the API will be available at:
- **Base URL**: `http://localhost:8000`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`

### API Endpoints
- `GET /health` — Check system health and service status
- `POST /auth/signup` — Register a new reviewer or applicant account
- `POST /auth/login` — Authenticate and retrieve user profile
- `POST /applications` — Upload application PDF and project name for multi-agent compliance audit
- `GET /applications` — List all reviewed applications and summary metrics
- `GET /applications/{id}` — Get application details, tracked issues, and execution trace
- `POST /applications/{id}/issues/{issue_id}/status` — Set reviewer decision (`Confirm` / `Dismiss`)
- `GET /applications/{id}/report` — Download official Review Report PDF

---

## Configuration
Set your environment variables in `.env`:
```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```
*(If no API key is configured, VYRO seamlessly operates in deterministic offline demo mode.)*
