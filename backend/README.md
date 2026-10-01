# 🛡️ VYRO Backend Architecture & Jury Guide

Welcome to the backend architecture documentation for **VYRO** — the Autonomous Multi-Agent Environmental Clearance (EC) Application Review System.

This folder (`backend/`) contains all the server-side business logic, AI agent orchestration, deterministic compliance scoring, database persistence, and REST API services.

---

## 📂 Backend File Organization

```
backend/
├── __init__.py            # Python package initialization & module exports
├── api.py                 # FastAPI REST API server (Swagger docs at /docs)
├── services.py            # Centralized business logic & service orchestration
├── review.py              # Application review pipeline & applicant followup loop
│
├── scoring.py             # Pure Python deterministic Clearance Readiness Scoring
├── ec_rules.py            # 18 Statutory MoEFCC EIA appraisal rules & weights
│
├── db.py                  # SQLite database engine (WAL mode, foreign keys, bcrypt)
├── models.py              # Pydantic v2 data schemas & validation models
│
├── extract.py             # PyMuPDF digital PDF text extractor
├── report.py              # ReportLab formal PDF review report generator
│
└── agents/                # Autonomous Multi-Agent AI Review Pipeline
    ├── __init__.py        # Multi-agent package setup
    ├── planner.py         # Planner Agent (goal formulation & document outline)
    ├── specialists.py     # 3 Specialist Agents (Completeness, Consistency, Contradictions)
    ├── verifier.py        # Verifier Agent (citation cross-checking & quote validation)
    └── tools.py           # Document search, numeric mentions & citation tools
```

---

## 🏛️ Core Architectural Subsystems

### 1. 🤖 Autonomous Multi-Agent AI Pipeline (`backend/agents/` & `backend/review.py`)
- **Planner Agent (`planner.py`)**: Analyzes document structure and decomposes compliance goals for specialist appraisal.
- **Completeness Specialist (`specialists.py`)**: Audits statutory EIA chapters (Baseline Air/Water/Noise, EMP budgets, EIA Notification 2006 checklist).
- **Consistency Specialist (`specialists.py`)**: Discovers quantitative contradictions (e.g., freshwater consumption vs. wastewater discharge).
- **Contradiction Specialist (`specialists.py`)**: Cross-references applicant claims against site disclosures.
- **Verifier Agent (`verifier.py`)**: Validates every cited page and extracts an exact verbatim quote ($\le 25$ words) directly from the text to eliminate LLM hallucinations.

---

### 2. ⚖️ Statutory Rules & Pure Python Scoring (`backend/ec_rules.py` & `backend/scoring.py`)
- **Zero External API / LLM Dependencies**: Completely deterministic, testable, and auditable arithmetic.
- **18 Statutory MoEFCC Rules**:
  - **6 Critical Rules (Weight = 3)**: Baseline Data, Public Hearing, ToR Compliance, Effluent/ZLD, Air Quality Modeling, ESZ/Wildlife Disclosures.
  - **8 Major Rules (Weight = 2)**: Hazardous Waste, 33% Greenbelt Allocation, EMP Budget, Water Balance, Disaster Plan, Cumulative Impacts, Fly Ash Utilization, CER Allocation.
  - **4 Minor Rules (Weight = 1)**: Rainwater Harvesting, Traffic Impact, Solar/Renewable Energy, Ambient Noise Limits.
- **Statutory Capping Rules**:
  - 1 Critical failure $\implies$ score is strictly capped at $\le 60\%$.
  - 2+ Critical failures $\implies$ score is strictly capped at $\le 40\%$.
- **Issue Penalties**:
  - Active Critical issue: $-5\%$
  - Active Major issue: $-2\%$
  - Dismissed issues: completely excluded ($0\%$ penalty).
- **Uncertainty Range**:
  - `range_low`: Treats unaddressed rules as failures.
  - `range_high`: Treats unaddressed rules as passes.
- **Readiness Bands**:
  - High ($\ge 85\%$), Moderate ($65 - 84\%$), Low ($40 - 64\%$), Very low ($< 40\%$).

---

### 3. 🗄️ Enterprise SQLite Database Layer (`backend/db.py`)
- **Database File**: `ec_app.db` located at workspace root.
- **Reliability PRAGMAs**:
  - `PRAGMA foreign_keys = ON;` enforced on every connection.
  - `PRAGMA journal_mode = WAL;` (Write-Ahead Logging) enables high-concurrency readers and writers without database locking.
  - `timeout = 30.0` prevents transient file lock timeouts.
- **Security & Data Integrity**:
  - 100% parameterized queries (`?`) to prevent SQL injection.
  - User passwords securely hashed with industry-standard `bcrypt` and salt.
  - Cascading deletes (`ON DELETE CASCADE`) maintain relational integrity between `applications` and `followups`.

---

### 4. 🌐 Service Layer & REST API (`backend/services.py` & `backend/api.py`)
- **Service Layer Pattern**: Zero Streamlit or UI code in the backend. All calculations, state mutations, and data conversions live here.
- **FastAPI Endpoints**:
  - `GET /health`: Health check and API version status.
  - `POST /review/upload`: Programmatic PDF report upload and full multi-agent audit execution.
  - `GET /projects`: List of all audited environmental clearance projects.
  - `GET /projects/{name}`: Comprehensive audit trace, readiness score, and tracked issues.
  - Interactive API documentation available at `http://localhost:8000/docs`.

---

### 5. 📄 Document Intelligence & PDF Generation (`backend/extract.py` & `backend/report.py`)
- **`extract.py`**: High-speed digital text extraction with PyMuPDF (`fitz`), maintaining page-by-page mapping.
- **`report.py`**: Generates a publication-quality formal EC Appraisal Report PDF using `ReportLab`, including the **Section 2: Statutory Clearance Readiness Appraisal**, metadata summary, and issue breakdown (excluding dismissed items).

---

## 🧪 Verification & Unit Testing

Run backend tests from workspace root:
```bash
# Test pure Python readiness scoring (6 comprehensive edge cases)
python scratch/test_scoring.py

# Test full multi-agent review pipeline end-to-end
python scratch/test_full_upload_end_to_end.py
```
