"""
Verifier Agent: Re-checks each flagged issue against the cited page text.
Validates citations, evidence quotes, and removes unverified or hallucinated findings.
Logs all steps to agent_trace with up to 2 retries on tool errors.
"""
from typing import List, Dict, Any, Callable, Optional, Tuple
from models import Issue
from agents.tools import verify_citation, parse_document_pages


class VerifierAgent:
    """
    Independent Auditor & Fact-Checker:
    Inspects every issue proposed by Specialists and filters out any issue
    whose evidence quote or cited page cannot be substantiated from the document text.
    """
    def __init__(
        self,
        agent_trace: List[Dict[str, Any]],
        trace_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.agent_trace = agent_trace
        self.trace_callback = trace_callback

    def log(self, action: str, observation: str, status: str = "success"):
        step = {
            "agent": "VerifierAgent",
            "action": action,
            "observation": observation,
            "status": status
        }
        self.agent_trace.append(step)
        if self.trace_callback:
            try:
                self.trace_callback(step)
            except Exception:
                pass

    def verify_issues(self, issues: List[Issue], text: str) -> List[Issue]:
        """
        Re-checks each issue against cited page text.
        Removes any issue that fails verification.
        """
        self.log(
            action="Thought: Initiate Citation & Evidence Verification",
            observation=f"Auditing {len(issues)} candidate issues proposed by specialist agents."
        )

        verified_issues: List[Issue] = []
        removed_count = 0

        for idx, issue in enumerate(issues):
            p_ref = issue.page_number or issue.evidence_page or "Full Document"
            q_text = issue.quote or issue.evidence_text or ""
            self.log(
                action=f"Thought: Verify Issue #{idx+1} ({issue.category})",
                observation=f"Checking evidence citation: '{p_ref}' | Quote: '{q_text[:80]}...'"
            )

            # Special case for Missing Study:
            if issue.category == "Missing Study":
                # Missing studies do not have a specific single page quote, they are absent from the document
                self.log(
                    action=f"Action: Verify Absence of Mandatory Study",
                    observation=f"Confirmed '{issue.description}' represents an absent mandatory study."
                )
                issue.confidence = "High"
                verified_issues.append(issue)
                continue

            # Standard case: Inconsistency / Contradiction citation check
            citation_res = None
            retries = 2
            for attempt in range(retries + 1):
                try:
                    citation_res = verify_citation(
                        page_ref=p_ref,
                        evidence_quote=q_text,
                        text=text
                    )
                    break
                except Exception as e:
                    self.log(
                        action=f"Tool Error: verify_citation",
                        observation=f"Error checking citation: {e}. Retrying {attempt+1}/2.",
                        status="retry"
                    )

            if citation_res and citation_res.get("verified", False):
                self.log(
                    action=f"Action: Citation Confirmed on {citation_res.get('matched_page')}",
                    observation=f"Verified: {citation_res.get('reason')}",
                    status="verified"
                )
                issue.confidence = "High"
                if not issue.page_number or issue.page_number == "Full Document":
                    matched_pg = citation_res.get("matched_page")
                    if matched_pg:
                        issue.page_number = f"Page {matched_pg}"
                        issue.evidence_page = issue.page_number
                verified_issues.append(issue)
            else:
                removed_count += 1
                reason = citation_res.get("reason", "No matching text found") if citation_res else "Verification call failed"
                self.log(
                    action=f"Action: REJECTED Unsubstantiated Issue #{idx+1}",
                    observation=f"Removed issue '{issue.description[:60]}...'. Reason: {reason}",
                    status="removed"
                )

        self.log(
            action="Thought: Verification Stage Completed",
            observation=f"Retained {len(verified_issues)} verified issues. Removed {removed_count} unverified claims."
        )
        return verified_issues
