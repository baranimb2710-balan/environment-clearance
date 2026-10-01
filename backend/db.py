"""
Database operations for the Environmental Clearance Application Review System (VYRO).
Uses Python's built-in sqlite3 module with WAL mode, foreign keys, and connection pooling/safety.
"""
import os
import sqlite3
import bcrypt
import hashlib
import json
from contextlib import contextmanager
from typing import Optional, Dict, Any, List

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_WORKSPACE_ROOT = os.path.abspath(os.path.join(_CURRENT_DIR, "..")) if os.path.basename(_CURRENT_DIR) == "backend" else _CURRENT_DIR
DB_PATH = os.path.join(_WORKSPACE_ROOT, "ec_app.db")


def get_db_connection() -> sqlite3.Connection:
    """Create and return a database connection configured with WAL mode, foreign keys, and timeout."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def db_session():
    """
    Context manager that guarantees transaction commit/rollback
    and explicit connection closing to eliminate connection leaks.
    """
    conn = get_db_connection()
    try:
        with conn:  # Context manager for transaction (commits on success, rolls back on error)
            yield conn
    finally:
        conn.close()


def hash_password(plain_password: str) -> str:
    """Hash a plain text password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def init_db():
    """Initialize database tables, apply automatic migrations, seed demo accounts, and create indexes."""
    with db_session() as conn:
        cursor = conn.cursor()
        
        # 1. Users table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                hashed_password TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('reviewer', 'applicant')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        
        # 2. Check if default demo reviewer account exists; seed if missing
        cursor.execute("SELECT username FROM users WHERE username = ?", ("admin",))
        admin_user = cursor.fetchone()
        if not admin_user:
            default_hashed_pwd = hash_password("admin123")
            cursor.execute(
                """
                INSERT INTO users (username, name, email, hashed_password, role)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("admin", "Default Reviewer", "admin@ecapp.gov", default_hashed_pwd, "reviewer")
            )

        # 3. Applications table for storing multi-agent execution trace and project audits
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                project_name TEXT PRIMARY KEY,
                owner_username TEXT DEFAULT 'admin',
                agent_trace TEXT,
                completeness_score INTEGER,
                summary TEXT,
                missing_studies TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Automatic migration: ensure owner_username, missing_studies, and readiness columns exist
        cursor.execute("PRAGMA table_info(applications)")
        app_cols = [row[1] for row in cursor.fetchall()]
        if "owner_username" not in app_cols:
            cursor.execute("ALTER TABLE applications ADD COLUMN owner_username TEXT DEFAULT 'admin'")
        if "missing_studies" not in app_cols:
            cursor.execute("ALTER TABLE applications ADD COLUMN missing_studies TEXT")
        if "readiness_score" not in app_cols:
            cursor.execute("ALTER TABLE applications ADD COLUMN readiness_score INTEGER")
        if "readiness_band" not in app_cols:
            cursor.execute("ALTER TABLE applications ADD COLUMN readiness_band TEXT")
        if "readiness_range_low" not in app_cols:
            cursor.execute("ALTER TABLE applications ADD COLUMN readiness_range_low INTEGER")
        if "readiness_range_high" not in app_cols:
            cursor.execute("ALTER TABLE applications ADD COLUMN readiness_range_high INTEGER")
        if "rule_results" not in app_cols:
            cursor.execute("ALTER TABLE applications ADD COLUMN rule_results TEXT")

        # 4. Follow-ups table with Foreign Key ON DELETE CASCADE
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS followups (
                issue_id TEXT PRIMARY KEY,
                project_name TEXT NOT NULL,
                category TEXT,
                severity TEXT,
                confidence TEXT DEFAULT 'Medium',
                description TEXT,
                page_number TEXT,
                quote TEXT,
                evidence_page TEXT,
                evidence_text TEXT,
                follow_up_question TEXT,
                status TEXT NOT NULL DEFAULT 'Open' CHECK(status IN ('Open', 'Resolved', 'Needs More Info', 'Still Open')),
                applicant_reply TEXT,
                ai_reason TEXT,
                reviewer_decision TEXT DEFAULT 'Pending',
                reviewer_comment TEXT,
                reviewed_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_name) REFERENCES applications(project_name) ON DELETE CASCADE
            )
            """
        )
        # Automatic safe migration: add columns using ALTER TABLE ADD COLUMN without dropping data
        cursor.execute("PRAGMA table_info(followups)")
        followup_cols = [row[1] for row in cursor.fetchall()]
        if "reviewer_decision" not in followup_cols:
            cursor.execute("ALTER TABLE followups ADD COLUMN reviewer_decision TEXT DEFAULT 'Pending'")
        if "confidence" not in followup_cols:
            cursor.execute("ALTER TABLE followups ADD COLUMN confidence TEXT DEFAULT 'Medium'")
        if "page_number" not in followup_cols:
            cursor.execute("ALTER TABLE followups ADD COLUMN page_number TEXT")
        if "quote" not in followup_cols:
            cursor.execute("ALTER TABLE followups ADD COLUMN quote TEXT")
        if "reviewer_comment" not in followup_cols:
            cursor.execute("ALTER TABLE followups ADD COLUMN reviewer_comment TEXT")
        if "reviewed_at" not in followup_cols:
            cursor.execute("ALTER TABLE followups ADD COLUMN reviewed_at TIMESTAMP")

        # Backfill existing records if page_number, quote, or confidence are NULL
        cursor.execute("UPDATE followups SET page_number = evidence_page WHERE (page_number IS NULL OR page_number = '') AND evidence_page IS NOT NULL")
        cursor.execute("UPDATE followups SET quote = evidence_text WHERE (quote IS NULL OR quote = '') AND evidence_text IS NOT NULL")
        cursor.execute("UPDATE followups SET confidence = 'Medium' WHERE confidence IS NULL OR confidence = ''")

        # Ensure foreign key constraint is present on existing followups table
        cursor.execute("PRAGMA foreign_key_list(followups)")
        existing_fks = cursor.fetchall()
        has_fk = any(row[2] == "applications" for row in existing_fks)
        if not has_fk:
            # Rebuild followups table with foreign key constraint enabled
            cursor.execute(
                """
                CREATE TABLE followups_migrated (
                    issue_id TEXT PRIMARY KEY,
                    project_name TEXT NOT NULL,
                    category TEXT,
                    severity TEXT,
                    confidence TEXT DEFAULT 'Medium',
                    description TEXT,
                    page_number TEXT,
                    quote TEXT,
                    evidence_page TEXT,
                    evidence_text TEXT,
                    follow_up_question TEXT,
                    status TEXT NOT NULL DEFAULT 'Open' CHECK(status IN ('Open', 'Resolved', 'Needs More Info', 'Still Open')),
                    applicant_reply TEXT,
                    ai_reason TEXT,
                    reviewer_decision TEXT DEFAULT 'Pending',
                    reviewer_comment TEXT,
                    reviewed_at TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_name) REFERENCES applications(project_name) ON DELETE CASCADE
                )
                """
            )
            cursor.execute(
                """
                INSERT OR IGNORE INTO followups_migrated (
                    issue_id, project_name, category, severity, confidence, description,
                    page_number, quote, evidence_page, evidence_text, follow_up_question, status,
                    applicant_reply, ai_reason, reviewer_decision, reviewer_comment, reviewed_at, updated_at
                )
                SELECT 
                    issue_id, project_name, category, severity, COALESCE(confidence, 'Medium'), description,
                    COALESCE(page_number, evidence_page), COALESCE(quote, evidence_text),
                    evidence_page, evidence_text, follow_up_question, status,
                    applicant_reply, ai_reason, COALESCE(reviewer_decision, 'Pending'),
                    reviewer_comment, reviewed_at, updated_at
                FROM followups
                """
            )
            cursor.execute("DROP TABLE followups;")
            cursor.execute("ALTER TABLE followups_migrated RENAME TO followups;")

        # 5. Performance and Integrity Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_followups_project_name ON followups(project_name);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_followups_updated_at ON followups(updated_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_followups_pname_status ON followups(project_name, status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_updated_at ON applications(updated_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_owner ON applications(owner_username);")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique ON users(email);")


def get_user(identifier: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single user by username, email, or name (case-insensitive)."""
    clean_id = identifier.strip().lower()
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM users 
            WHERE LOWER(username) = ? OR LOWER(email) = ? OR LOWER(name) = ?
            LIMIT 1
            """,
            (clean_id, clean_id, clean_id)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None


def get_all_users() -> List[Dict[str, Any]]:
    """Retrieve all registered users."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, name, email, role, created_at FROM users")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_authenticator_credentials() -> Dict[str, Any]:
    """
    Format credentials dictionary suitable for streamlit-authenticator.
    Allows login via username, email, or name with case flexibility.
    """
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, name, email, hashed_password, role FROM users")
        rows = cursor.fetchall()
        
        credentials = {"usernames": {}}
        for row in rows:
            u_clean = row["username"].strip()
            email_clean = row["email"].strip()
            name_clean = row["name"].strip()
            
            user_data = {
                "name": row["name"],
                "password": row["hashed_password"],
                "email": row["email"],
                "role": row["role"],
                "roles": [row["role"]],
                "logged_in": False
            }
            # Register username variants
            for k in [u_clean, u_clean.lower(), u_clean.capitalize(), u_clean.upper()]:
                if k:
                    credentials["usernames"][k] = user_data
                    
            # Register email variants
            for k in [email_clean, email_clean.lower()]:
                if k:
                    credentials["usernames"][k] = user_data
                    
            # Register name variants if unique
            if name_clean and name_clean.lower() not in credentials["usernames"]:
                credentials["usernames"][name_clean] = user_data
                credentials["usernames"][name_clean.lower()] = user_data
                credentials["usernames"][name_clean.capitalize()] = user_data

        return credentials


def create_user(username: str, name: str, email: str, plain_password: str, role: str) -> tuple[bool, str]:
    """
    Register a new user in SQLite after hashing their password.
    Returns: (success: bool, message: str)
    """
    username_clean = username.strip().lower()
    email_clean = email.strip().lower()
    if not username_clean:
        return False, "Username cannot be empty."
    if not email_clean:
        return False, "Email cannot be empty."
    
    if role not in ("reviewer", "applicant"):
        return False, "Role must be either 'reviewer' or 'applicant'."
        
    hashed = hash_password(plain_password)
    
    try:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT username, email FROM users WHERE LOWER(username) = ? OR LOWER(email) = ?",
                (username_clean, email_clean)
            )
            existing = cursor.fetchone()
            if existing:
                if existing["username"].lower() == username_clean:
                    return False, f"Username '{username_clean}' already exists."
                else:
                    return False, f"Email '{email_clean}' is already registered."

            cursor.execute(
                """
                INSERT INTO users (username, name, email, hashed_password, role)
                VALUES (?, ?, ?, ?, ?)
                """,
                (username_clean, name.strip(), email_clean, hashed, role)
            )
            return True, "User registered successfully!"
    except sqlite3.IntegrityError as ie:
        if "email" in str(ie).lower():
            return False, f"Email '{email_clean}' is already registered."
        return False, f"Username '{username_clean}' already exists."
    except Exception as e:
        return False, f"Database error: {str(e)}"


def sync_review_issues(project_name: str, issues: List[Any]) -> List[Any]:
    """
    Synchronizes in-memory review issues with the SQLite followups table.
    Preserves existing applicant replies, AI reasons, reviewer decisions, comments, and statuses.
    Uses content-addressed stable hashing to avoid index drift.
    """
    clean_pname = project_name.strip()
    with db_session() as conn:
        cursor = conn.cursor()
        for issue in issues:
            if not getattr(issue, "id", None):
                # Content-addressed stable hash (independent of list order)
                raw_hash = hashlib.sha256(
                    f"{clean_pname}_{issue.description}_{issue.category}_{getattr(issue, 'evidence_page', '') or ''}_{getattr(issue, 'page_number', '') or ''}".encode()
                ).hexdigest()[:12]
                issue.id = f"iss_{raw_hash}"

            cursor.execute(
                """
                SELECT status, applicant_reply, ai_reason, reviewer_decision,
                       reviewer_comment, reviewed_at, page_number, quote, confidence
                FROM followups WHERE issue_id = ?
                """,
                (issue.id,)
            )
            row = cursor.fetchone()
            if row:
                issue.status = row["status"]
                issue.applicant_reply = row["applicant_reply"]
                issue.ai_reason = row["ai_reason"]
                issue.reviewer_decision = row["reviewer_decision"] or "Pending"
                if "reviewer_comment" in row.keys() and row["reviewer_comment"]:
                    issue.reviewer_comment = row["reviewer_comment"]
                if "reviewed_at" in row.keys() and row["reviewed_at"]:
                    issue.reviewed_at = str(row["reviewed_at"])
                if "page_number" in row.keys() and row["page_number"]:
                    issue.page_number = row["page_number"]
                    issue.evidence_page = row["page_number"]
                if "quote" in row.keys() and row["quote"]:
                    issue.quote = row["quote"]
                    issue.evidence_text = row["quote"]
                if "confidence" in row.keys() and row["confidence"]:
                    issue.confidence = row["confidence"]
            else:
                decision = getattr(issue, "reviewer_decision", "Pending") or "Pending"
                p_num = getattr(issue, "page_number", None) or getattr(issue, "evidence_page", None)
                q_text = getattr(issue, "quote", None) or getattr(issue, "evidence_text", None)
                conf = getattr(issue, "confidence", "Medium") or "Medium"
                r_comment = getattr(issue, "reviewer_comment", None)
                r_at = getattr(issue, "reviewed_at", None)

                cursor.execute(
                    """
                    INSERT INTO followups (
                        issue_id, project_name, category, severity, confidence, description,
                        page_number, quote, evidence_page, evidence_text, follow_up_question,
                        status, applicant_reply, ai_reason, reviewer_decision, reviewer_comment, reviewed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        issue.id, clean_pname, issue.category, issue.severity, conf,
                        issue.description, p_num, q_text, p_num, q_text,
                        issue.follow_up_question, issue.status, issue.applicant_reply,
                        issue.ai_reason, decision, r_comment, r_at
                    )
                )
    return issues


def update_issue_followup(issue_id: str, status: str, applicant_reply: str, ai_reason: str) -> bool:
    """Updates the status, reply, and AI rationale of an issue in the followups table."""
    try:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE followups 
                SET status = ?, applicant_reply = ?, ai_reason = ?, updated_at = CURRENT_TIMESTAMP
                WHERE issue_id = ?
                """,
                (status, applicant_reply, ai_reason, issue_id)
            )
            return True
    except Exception as e:
        print(f"Error updating issue followup: {e}")
        return False


def recalculate_project_readiness(project_name: str) -> Optional[Dict[str, Any]]:
    """
    Recalculates the Clearance Readiness Score from stored rule_results and current followups.
    Updates the applications table with the recalculated score, band, and range.
    """
    clean_pname = project_name.strip()
    try:
        from scoring import calculate_readiness
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT rule_results FROM applications WHERE project_name = ?",
                (clean_pname,)
            )
            app_row = cursor.fetchone()
            if not app_row:
                return None
            
            raw_rules = app_row["rule_results"]
            rule_evals = json.loads(raw_rules) if raw_rules else []
            
            # Fetch all followups
            cursor.execute(
                "SELECT * FROM followups WHERE project_name = ?",
                (clean_pname,)
            )
            issues = [dict(r) for r in cursor.fetchall()]
            
            readiness_data = calculate_readiness(rule_evals, issues)
            
            cursor.execute(
                """
                UPDATE applications
                SET readiness_score = ?,
                    readiness_band = ?,
                    readiness_range_low = ?,
                    readiness_range_high = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE project_name = ?
                """,
                (
                    readiness_data["score"],
                    readiness_data["band"],
                    readiness_data["range_low"],
                    readiness_data["range_high"],
                    clean_pname
                )
            )
            return readiness_data
    except Exception as e:
        print(f"Error recalculating readiness for {project_name}: {e}")
        return None


def update_reviewer_action(issue_id: str, decision: str, comment: Optional[str] = None) -> bool:
    """
    Updates reviewer_decision ('Confirmed' or 'Dismissed'), optional reviewer_comment,
    and reviewed_at timestamp for an issue in SQLite.
    Automatically triggers recalculation of the project's Clearance Readiness Score.
    """
    project_name = None
    try:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE followups
                SET reviewer_decision = ?,
                    reviewer_comment = CASE WHEN ? IS NOT NULL AND ? != '' THEN ? ELSE reviewer_comment END,
                    reviewed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE issue_id = ?
                """,
                (decision, comment, comment, comment, issue_id)
            )
            # Find project_name
            cursor.execute("SELECT project_name FROM followups WHERE issue_id = ?", (issue_id,))
            p_row = cursor.fetchone()
            if p_row and p_row["project_name"]:
                project_name = p_row["project_name"]

        # Recalculate AFTER the previous transaction commits and releases lock
        if project_name:
            recalculate_project_readiness(project_name)
        return True
    except Exception as e:
        print(f"Error updating reviewer action: {e}")
        return False


def update_reviewer_decision(issue_id: str, decision: str) -> bool:
    """Updates reviewer_decision ('Confirmed' or 'Dismissed') for an issue in SQLite."""
    return update_reviewer_action(issue_id, decision, None)


def get_project_followups(project_name: str) -> List[Dict[str, Any]]:
    """Retrieve all follow-up issues for a project."""
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM followups WHERE project_name = ? ORDER BY issue_id",
            (project_name.strip(),)
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def get_all_projects_with_followups(username: Optional[str] = None, role: Optional[str] = None) -> List[str]:
    """
    Retrieve list of distinct project names that have followups.
    If role == 'applicant' and username is provided, filters to projects owned by that user.
    Reviewers or unauthenticated requests receive all projects.
    """
    with db_session() as conn:
        cursor = conn.cursor()
        if role == "applicant" and username:
            # Query projects owned by applicant, or legacy projects with no owner assigned
            cursor.execute(
                """
                SELECT DISTINCT project_name FROM applications 
                WHERE owner_username = ? OR owner_username IS NULL OR owner_username = 'admin'
                ORDER BY updated_at DESC
                """,
                (username.strip(),)
            )
            rows = cursor.fetchall()
            if rows:
                return [r["project_name"] for r in rows]

        cursor.execute("SELECT DISTINCT project_name FROM followups ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        return [r["project_name"] for r in rows]


def store_application_trace(
    project_name: str,
    agent_trace: Any,
    completeness_score: Optional[int] = None,
    summary: Optional[str] = None,
    owner_username: Optional[str] = None,
    missing_studies: Optional[List[str]] = None,
    readiness_score: Optional[int] = None,
    readiness_band: Optional[str] = None,
    readiness_range_low: Optional[int] = None,
    readiness_range_high: Optional[int] = None,
    rule_results: Optional[Any] = None
) -> bool:
    """
    Stores or updates the multi-agent execution trace and metadata for an application in SQLite.
    Stores agent_trace, missing_studies, and rule_results in applications table as JSON text.
    """
    clean_pname = project_name.strip()
    trace_json = json.dumps(agent_trace) if not isinstance(agent_trace, str) else agent_trace
    missing_json = json.dumps(missing_studies) if missing_studies is not None else None
    
    if rule_results is not None:
        if isinstance(rule_results, str):
            rules_json = rule_results
        else:
            # Convert models to dicts if needed
            serializable = [r.model_dump() if hasattr(r, "model_dump") else r for r in rule_results]
            rules_json = json.dumps(serializable)
    else:
        rules_json = None

    try:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO applications (
                    project_name, owner_username, agent_trace, completeness_score,
                    summary, missing_studies, readiness_score, readiness_band,
                    readiness_range_low, readiness_range_high, rule_results, updated_at
                )
                VALUES (?, COALESCE(?, 'admin'), ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(project_name) DO UPDATE SET
                    owner_username = COALESCE(excluded.owner_username, applications.owner_username),
                    agent_trace = excluded.agent_trace,
                    completeness_score = COALESCE(excluded.completeness_score, applications.completeness_score),
                    summary = COALESCE(excluded.summary, applications.summary),
                    missing_studies = COALESCE(excluded.missing_studies, applications.missing_studies),
                    readiness_score = COALESCE(excluded.readiness_score, applications.readiness_score),
                    readiness_band = COALESCE(excluded.readiness_band, applications.readiness_band),
                    readiness_range_low = COALESCE(excluded.readiness_range_low, applications.readiness_range_low),
                    readiness_range_high = COALESCE(excluded.readiness_range_high, applications.readiness_range_high),
                    rule_results = COALESCE(excluded.rule_results, applications.rule_results),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    clean_pname, owner_username, trace_json, completeness_score,
                    summary, missing_json, readiness_score, readiness_band,
                    readiness_range_low, readiness_range_high, rules_json
                )
            )
            return True
    except Exception as e:
        print(f"Error storing application trace: {e}")
        return False


def get_application_trace(project_name: str) -> List[Dict[str, Any]]:
    """Retrieves the stored multi-agent execution trace for a project."""
    clean_pname = project_name.strip()
    try:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT agent_trace FROM applications WHERE project_name = ?", (clean_pname,))
            row = cursor.fetchone()
            if row and row["agent_trace"]:
                return json.loads(row["agent_trace"])
    except Exception as e:
        print(f"Error fetching application trace: {e}")
    return []


def get_application_record(project_name: str) -> Optional[Dict[str, Any]]:
    """Retrieves the full application record from the applications table."""
    clean_pname = project_name.strip()
    try:
        with db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM applications WHERE project_name = ?", (clean_pname,))
            row = cursor.fetchone()
            if row:
                return dict(row)
    except Exception as e:
        print(f"Error fetching application record: {e}")
    return None
