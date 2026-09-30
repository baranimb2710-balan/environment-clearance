"""
Database operations for the Environmental Clearance Application Review System.
Uses Python's built-in sqlite3 module.
"""
import os
import sqlite3
import bcrypt
from typing import Optional, Dict, Any, List

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ec_app.db")


def get_db_connection() -> sqlite3.Connection:
    """Create and return a database connection with dictionary-like row access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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
    """Initialize database tables and seed default demo accounts."""
    with get_db_connection() as conn:
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
            conn.commit()

        # 3. Follow-ups table for applicant clarification loop & reviewer decisions
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS followups (
                issue_id TEXT PRIMARY KEY,
                project_name TEXT NOT NULL,
                category TEXT,
                severity TEXT,
                description TEXT,
                evidence_page TEXT,
                evidence_text TEXT,
                follow_up_question TEXT,
                status TEXT NOT NULL DEFAULT 'Open' CHECK(status IN ('Open', 'Resolved', 'Needs More Info', 'Still Open')),
                applicant_reply TEXT,
                ai_reason TEXT,
                reviewer_decision TEXT DEFAULT 'Pending',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # Automatic migration: ensure reviewer_decision column exists if table was created previously
        cursor.execute("PRAGMA table_info(followups)")
        columns = [row[1] for row in cursor.fetchall()]
        if "reviewer_decision" not in columns:
            cursor.execute("ALTER TABLE followups ADD COLUMN reviewer_decision TEXT DEFAULT 'Pending'")

        conn.commit()


def get_user(identifier: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single user by username, email, or name (case-insensitive)."""
    clean_id = identifier.strip().lower()
    with get_db_connection() as conn:
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
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, name, email, role, created_at FROM users")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_authenticator_credentials() -> Dict[str, Any]:
    """
    Format credentials dictionary suitable for streamlit-authenticator.
    Allows login via username, email, or name with case flexibility.
    """
    with get_db_connection() as conn:
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
    if not username_clean:
        return False, "Username cannot be empty."
    
    if role not in ("reviewer", "applicant"):
        return False, "Role must be either 'reviewer' or 'applicant'."
        
    hashed = hash_password(plain_password)
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (username, name, email, hashed_password, role)
                VALUES (?, ?, ?, ?, ?)
                """,
                (username_clean, name.strip(), email.strip().lower(), hashed, role)
            )
            conn.commit()
            return True, "User registered successfully!"
    except sqlite3.IntegrityError:
        return False, f"Username '{username_clean}' already exists."
    except Exception as e:
        return False, f"Database error: {str(e)}"


def sync_review_issues(project_name: str, issues: List[Any]) -> List[Any]:
    """
    Synchronizes in-memory review issues with the SQLite followups table.
    Preserves existing applicant replies, AI reasons, and statuses.
    """
    import hashlib
    clean_pname = project_name.strip()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for idx, issue in enumerate(issues):
            if not getattr(issue, "id", None):
                raw_hash = hashlib.md5(f"{clean_pname}_{issue.description}_{idx}".encode()).hexdigest()[:8]
                issue.id = f"iss_{raw_hash}"

            cursor.execute("SELECT status, applicant_reply, ai_reason, reviewer_decision FROM followups WHERE issue_id = ?", (issue.id,))
            row = cursor.fetchone()
            if row:
                issue.status = row["status"]
                issue.applicant_reply = row["applicant_reply"]
                issue.ai_reason = row["ai_reason"]
                issue.reviewer_decision = row["reviewer_decision"] or "Pending"
            else:
                decision = getattr(issue, "reviewer_decision", "Pending") or "Pending"
                cursor.execute(
                    """
                    INSERT INTO followups (
                        issue_id, project_name, category, severity, description,
                        evidence_page, evidence_text, follow_up_question, status,
                        applicant_reply, ai_reason, reviewer_decision
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        issue.id, clean_pname, issue.category, issue.severity,
                        issue.description, issue.evidence_page, issue.evidence_text,
                        issue.follow_up_question, issue.status, issue.applicant_reply,
                        issue.ai_reason, decision
                    )
                )
        conn.commit()
    return issues


def update_issue_followup(issue_id: str, status: str, applicant_reply: str, ai_reason: str) -> bool:
    """Updates the status, reply, and AI rationale of an issue in the followups table."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE followups 
                SET status = ?, applicant_reply = ?, ai_reason = ?, updated_at = CURRENT_TIMESTAMP
                WHERE issue_id = ?
                """,
                (status, applicant_reply, ai_reason, issue_id)
            )
            conn.commit()
            return True
    except Exception as e:
        print(f"Error updating issue followup: {e}")
        return False


def update_reviewer_decision(issue_id: str, decision: str) -> bool:
    """Updates reviewer_decision ('Confirmed' or 'Dismissed') for an issue in SQLite."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE followups
                SET reviewer_decision = ?, updated_at = CURRENT_TIMESTAMP
                WHERE issue_id = ?
                """,
                (decision, issue_id)
            )
            conn.commit()
            return True
    except Exception as e:
        print(f"Error updating reviewer decision: {e}")
        return False



def get_project_followups(project_name: str) -> List[Dict[str, Any]]:
    """Retrieve all follow-up issues for a project."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM followups WHERE project_name = ? ORDER BY issue_id",
            (project_name.strip(),)
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def get_all_projects_with_followups() -> List[str]:
    """Retrieve list of distinct project names that have followups."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT project_name FROM followups ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        return [r["project_name"] for r in rows]

