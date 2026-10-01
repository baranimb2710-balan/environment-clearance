"""
Planner Agent: Builds a Pydantic-validated goal list from report text.
Allocates specific audit mandates to the Completeness, Consistency, and Contradiction specialists.
Includes retry logic on validation errors and logs steps to agent_trace.
"""
import os
import re
import json
from typing import List, Dict, Any, Literal, Callable, Optional
from pydantic import BaseModel, Field
import anthropic
from agents.tools import parse_document_pages, EC_CHECKLIST


class AuditGoal(BaseModel):
    id: str = Field(..., description="Unique goal ID, e.g. 'GOAL-01'")
    specialist: Literal["Completeness", "Consistency", "Contradiction"] = Field(
        ..., description="Specialist agent assigned to this goal"
    )
    description: str = Field(..., description="Specific directive or scope for the specialist")
    target_aspects: List[str] = Field(
        default_factory=list, description="Target environmental parameters, chapters, or figures to scrutinize"
    )
    priority: int = Field(1, description="Execution priority (1=Highest)")


class PlannerOutput(BaseModel):
    project_title: str = Field(..., description="Title or name of the project identified from report")
    goals: List[AuditGoal] = Field(..., min_items=1, description="List of audit goals")
    executive_overview: str = Field(..., description="Preliminary high-level structural overview")


def clean_json_string(raw_text: str) -> str:
    """Extracts JSON content from potential markdown wrapper."""
    raw_text = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
    if match:
        return match.group(1).strip()
    start = raw_text.find("{")
    end = raw_text.rfind("}")
    if start != -1 and end != -1:
        return raw_text[start:end + 1].strip()
    return raw_text


def simulate_planner(text: str, project_name: str) -> PlannerOutput:
    """Deterministic fallback planner for demo mode or offline environments."""
    pages = parse_document_pages(text)
    num_pages = len(pages)
    
    return PlannerOutput(
        project_title=project_name,
        goals=[
            AuditGoal(
                id="GOAL-COMPLETENESS",
                specialist="Completeness",
                description=f"Audit entire {num_pages}-page document against the 8 mandatory Environmental Clearance baseline studies.",
                target_aspects=EC_CHECKLIST,
                priority=1
            ),
            AuditGoal(
                id="GOAL-CONSISTENCY",
                specialist="Consistency",
                description="Cross-compare daily freshwater intake, water balance tables, greenbelt acreage, and stack heights across chapters.",
                target_aspects=["water demand", "water balance", "greenbelt", "stack emission", "cost"],
                priority=2
            ),
            AuditGoal(
                id="GOAL-CONTRADICTION",
                specialist="Contradiction",
                description="Detect conflicting claims between developer assertions (e.g. zero groundwater depletion, zero air deterioration) and baseline tables.",
                target_aspects=["groundwater stress", "baseline air quality", "biodiversity impact"],
                priority=3
            )
        ],
        executive_overview=f"Detected {num_pages} digital pages for '{project_name}'. Mandated 3 specialist review branches."
    )


def run_planner(
    text: str,
    project_name: str,
    agent_trace: List[Dict[str, Any]],
    trace_callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> PlannerOutput:
    """
    Executes the Planner Agent.
    Builds a goal list from report text with Pydantic validation, retrying up to 2 times on error.
    Appends steps to agent_trace.
    """
    def log_step(action: str, observation: str, status: str = "success"):
        step = {
            "agent": "Planner",
            "action": action,
            "observation": observation,
            "status": status
        }
        agent_trace.append(step)
        if trace_callback:
            try:
                trace_callback(step)
            except Exception:
                pass

    log_step(
        action="Document Structural Ingestion",
        observation=f"Ingesting text for '{project_name}' ({len(text)} characters). Parsing page boundaries."
    )

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or "your_" in api_key.lower() or len(api_key.strip()) < 10:
        log_step(
            action="Generate Plan (Deterministic Engine)",
            observation="Operating with deterministic multi-agent planner. Formulating 3 specialist audit goals."
        )
        plan = simulate_planner(text, project_name)
        log_step(
            action="Goal Formulation Completed",
            observation=f"Generated {len(plan.goals)} audit goals across Completeness, Consistency, and Contradiction."
        )
        return plan

    client = anthropic.Anthropic(api_key=api_key.strip())
    pages = parse_document_pages(text)
    preview = "\n\n".join(f"--- Page {p} ---\n{content[:600]}" for p, content in list(pages.items())[:6])

    prompt = f"""
You are the Lead Audit Planner in the VYRO Multi-Agent Environmental Clearance System.
Analyze the following report excerpt for project '{project_name}' and generate a structured audit plan.

Report Excerpt:
{preview}

Mandatory Checklist:
{', '.join(EC_CHECKLIST)}

Formulate specific goals for 3 specialist agents:
1. "Completeness" specialist: Check mandatory baseline studies.
2. "Consistency" specialist: Compare numerical data across pages (e.g. water balance, land area, stack emissions).
3. "Contradiction" specialist: Check developer claims against empirical baseline data.

Return strictly valid JSON matching this schema:
{{
  "project_title": "{project_name}",
  "goals": [
    {{
      "id": "GOAL-01",
      "specialist": "Completeness",
      "description": "Examine checklist coverage",
      "target_aspects": ["EIA", "EMP", "biodiversity"],
      "priority": 1
    }}
  ],
  "executive_overview": "Structural overview paragraph."
}}
"""

    last_error = None
    # Retry loop up to 2 retries
    for attempt in range(3):
        try:
            curr_prompt = prompt
            if attempt > 0 and last_error:
                log_step(
                    action=f"Retry Attempt #{attempt}",
                    observation=f"Feeding previous validation error back to Planner: {last_error}",
                    status="retry"
                )
                curr_prompt += f"\n\nCRITICAL FIX: Your previous response failed validation with: {last_error}. Return strictly valid JSON."

            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1500,
                temperature=0.1,
                system="You are an expert AI Lead Planner for Environmental Clearance Audits. Always output strict JSON.",
                messages=[{"role": "user", "content": curr_prompt}]
            )

            raw_out = response.content[0].text
            clean_out = clean_json_string(raw_out)
            plan = PlannerOutput.model_validate_json(clean_out)
            
            log_step(
                action="Plan Formulation Verified",
                observation=f"Generated {len(plan.goals)} audit goals. Overview: {plan.executive_overview[:100]}..."
            )
            return plan

        except Exception as e:
            last_error = str(e)
            if attempt == 2:
                log_step(
                    action="Planner Fallback Activated",
                    observation=f"Anthropic API plan validation failed after retries ({last_error}). Falling back to deterministic plan.",
                    status="fallback"
                )
                return simulate_planner(text, project_name)

    return simulate_planner(text, project_name)
