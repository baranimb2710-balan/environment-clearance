"""
Pydantic models for data validation, user management, structured review outputs,
and applicant follow-up loop verification.
"""
from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator


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
    severity: Literal["Critical", "Major", "Minor", "High", "Medium", "Low"] = Field(
        "Major", description="Severity level: Critical, Major, or Minor"
    )
    confidence: Literal["High", "Medium", "Low"] = Field(
        "Medium", description="Confidence assessment: High, Medium, or Low"
    )
    description: str = Field(
        ..., description="Clear explanation of the detected problem"
    )
    page_number: Optional[str] = Field(
        None, description="Page number(s) where evidence was identified (e.g. 'Page 4' or 'Page 2 vs Page 3')"
    )
    quote: Optional[str] = Field(
        None, description="Short exact quote from the report (max 25 words)"
    )
    evidence_page: Optional[str] = Field(
        None, description="Legacy page citation reference"
    )
    evidence_text: Optional[str] = Field(
        None, description="Legacy evidence quote reference"
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
    reviewer_comment: Optional[str] = Field(
        None, description="Optional reviewer feedback, rationale, or review comments"
    )
    reviewed_at: Optional[str] = Field(
        None, description="Timestamp when reviewer confirmed or dismissed the issue"
    )

    @model_validator(mode="after")
    def normalize_fields(self):
        # 1. Normalize severity (High -> Critical, Medium -> Major, Low -> Minor)
        sev_map = {"High": "Critical", "Medium": "Major", "Low": "Minor"}
        if self.severity in sev_map:
            self.severity = sev_map[self.severity]

        # 2. Synchronize page_number <-> evidence_page
        if self.page_number and not self.evidence_page:
            self.evidence_page = self.page_number
        elif self.evidence_page and not self.page_number:
            self.page_number = self.evidence_page

        # 3. Synchronize quote <-> evidence_text and enforce max 25 words
        raw_quote = self.quote or self.evidence_text
        if raw_quote:
            words = raw_quote.strip().split()
            if len(words) > 25:
                clipped = " ".join(words[:25]) + "..."
            else:
                clipped = raw_quote.strip()
            self.quote = clipped
            self.evidence_text = clipped
        return self


class RuleEvaluation(BaseModel):
    """Evaluation result for one of the 18 statutory EC appraisal rules."""
    rule_id: str = Field(..., description="Rule ID, e.g. 'EC-R01'")
    rule_name: str = Field(..., description="Rule title")
    category: Literal["Critical", "Major", "Minor"] = Field(..., description="Rule criticality category")
    weight: int = Field(..., description="Rule weight: 3 for Critical, 2 for Major, 1 for Minor")
    status: Literal["pass", "partial", "fail", "not_found"] = Field(
        ..., description="Evaluation outcome: pass, partial, fail, or not_found"
    )
    reason: str = Field(..., description="Short explanation of compliance assessment")
    page_number: Optional[str] = Field(None, description="Page number(s) citing evidence")
    quote: Optional[str] = Field(None, description="Short exact quote from the report (max 25 words)")

    @property
    def id(self) -> str:
        return self.rule_id

    @property
    def name(self) -> str:
        return self.rule_name

    @model_validator(mode="after")
    def validate_quote(self):
        if self.quote:
            words = self.quote.strip().split()
            if len(words) > 25:
                self.quote = " ".join(words[:25]) + "..."
            else:
                self.quote = self.quote.strip()
        return self


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
    rule_results: List[RuleEvaluation] = Field(
        default_factory=list, description="Evaluations of the 18 statutory EC rules"
    )
    readiness_score: Optional[int] = Field(
        None, description="Clearance Readiness Score (0-100)"
    )
    readiness_band: Optional[str] = Field(
        None, description="Readiness band: High, Moderate, Low, or Very low"
    )
    readiness_range_low: Optional[int] = Field(
        None, description="Lower bound of readiness score"
    )
    readiness_range_high: Optional[int] = Field(
        None, description="Upper bound of readiness score"
    )
    readiness_category_counts: Optional[Dict[str, Dict[str, int]]] = Field(
        default_factory=dict, description="Rule counts by category and status"
    )
    readiness_improvements: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, description="Top 3 recommended improvements sorted by score gain"
    )



class FollowupResult(BaseModel):
    """Output schema for AI evaluation of an applicant's follow-up clarification."""
    status: Literal["Resolved", "Still Open"] = Field(
        ..., description="Resolution status ('Resolved' if satisfactorily addressed, otherwise 'Still Open')"
    )
    reason: str = Field(
        ..., description="Clear explanation for the decision citing the applicant reply and supporting data"
    )
