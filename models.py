"""
Pydantic models for data validation, user management, structured review outputs,
and applicant follow-up loop verification.
"""
from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field


class UserRole:
    REVIEWER = "reviewer"
    APPLICANT = "applicant"
    ALL = [REVIEWER, APPLICANT]


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    name: str = Field(..., min_length=2, max_length=100, description="Full name")
    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", description="Valid email address")
    password: str = Field(..., min_length=6, description="Raw password (will be hashed with bcrypt)")
    role: Literal["reviewer", "applicant"] = Field(..., description="User role")


class UserProfile(BaseModel):
    username: str
    name: str
    email: str
    role: Literal["reviewer", "applicant"]
    created_at: Optional[str] = None


class Issue(BaseModel):
    """Represents a flagged environmental discrepancy, missing study, or contradiction."""
    id: Optional[str] = Field(None, description="Unique issue identifier")
    category: Literal["Missing Study", "Inconsistency", "Contradiction"] = Field(
        ..., description="Category of the detected issue"
    )
    severity: Literal["High", "Medium", "Low"] = Field(
        ..., description="Severity level of the issue (High, Medium, or Low)"
    )
    description: str = Field(
        ..., description="Clear explanation of the detected problem"
    )
    evidence_page: Optional[str] = Field(
        None, description="Page number(s) where the evidence was identified (e.g. 'Page 4' or 'Page 2 vs Page 18')"
    )
    evidence_text: Optional[str] = Field(
        None, description="Direct quote or numeric evidence extracted from the document"
    )
    follow_up_question: Optional[str] = Field(
        None, description="Deficiency question or clarification directed to the project applicant"
    )
    status: Literal["Open", "Resolved", "Needs More Info", "Still Open"] = Field(
        "Open", description="Current resolution status"
    )
    applicant_reply: Optional[str] = Field(
        None, description="The applicant's submitted explanation or clarification"
    )
    ai_reason: Optional[str] = Field(
        None, description="The AI's compliance reasoning for the resolution decision"
    )
    reviewer_decision: Optional[Literal["Confirmed", "Dismissed", "Pending"]] = Field(
        "Pending", description="Reviewer assessment: Confirmed, Dismissed, or Pending"
    )


class ReviewResult(BaseModel):
    """Structured output for the full Environmental Clearance report audit."""
    project_name: str = Field(..., description="Name of the project")
    completeness_score: int = Field(
        ..., ge=0, le=100, description="Completeness score between 0 and 100"
    )
    missing_studies: List[str] = Field(
        default_factory=list, description="Mandatory studies missing from the application"
    )
    issues: List[Issue] = Field(
        default_factory=list, description="List of detected inconsistencies, gaps, and contradictions"
    )
    summary: str = Field(
        ..., description="Executive summary paragraph detailing the review assessment"
    )
    agent_trace: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, description="Execution trace steps recorded across multi-agent review pipeline"
    )



class FollowupResult(BaseModel):
    """Output schema for AI evaluation of an applicant's follow-up clarification."""
    status: Literal["Resolved", "Still Open"] = Field(
        ..., description="Resolution status ('Resolved' if satisfactorily addressed, otherwise 'Still Open')"
    )
    reason: str = Field(
        ..., description="Clear explanation for the decision citing the applicant reply and supporting data"
    )
