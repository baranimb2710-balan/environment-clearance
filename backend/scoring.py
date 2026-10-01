"""
Clearance Readiness Scoring Engine.
Pure Python module (NO LLM / external API calls) implementing the statutory
readiness scoring formula, critical failure caps, issue penalties, uncertainty bounds,
category status counts, and top score improvement recommendations.
"""
from typing import List, Dict, Any, Union, Tuple
from ec_rules import EC_RULES, get_all_rules


def _get_val(obj: Any, key: str, default: Any = None) -> Any:
    """Helper to extract attribute from Pydantic model or key from dict."""
    if hasattr(obj, key):
        val = getattr(obj, key)
        return val if val is not None else default
    elif isinstance(obj, dict):
        return obj.get(key, default)
    return default


def calculate_readiness(
    rule_results: List[Any],
    issues: List[Any]
) -> Dict[str, Any]:
    """
    Calculates the Environmental Clearance Readiness Score.

    Formula:
      - Points per rule: pass = 1.0, partial = 0.5, fail = 0.0, not_found = 0.0
      - Base % = (sum(weight * points) / sum(weight)) * 100
      - Critical Caps:
          * 1 critical fail  -> score capped at max 60%
          * 2+ critical fails -> score capped at max 40%
      - Penalties:
          * Confirmed or Pending Critical issue -> -5 points
          * Confirmed or Pending Major issue    -> -2 points
          * Dismissed issues excluded
      - Score floor: never below 0
      - Bands:
          * High: >= 85
          * Moderate: 65 - 84
          * Low: 40 - 64
          * Very low: < 40
      - Range:
          * range_low: treat not_found rules as fail
          * range_high: treat not_found rules as pass
      - Category counts: breakdowns for Critical, Major, Minor
      - Top 3 improvements: rules with highest potential score gain
    """
    total_weight = sum(r["weight"] for r in EC_RULES)
    if total_weight == 0:
        total_weight = 38

    # Index evaluations by rule_id
    eval_map = {}
    for r in rule_results:
        rid = _get_val(r, "rule_id") or _get_val(r, "id")
        if rid:
            eval_map[rid] = r

    # Build canonical list of 18 rule evaluations
    canonical_evals = []
    for ref_rule in EC_RULES:
        rid = ref_rule["id"]
        ev = eval_map.get(rid)
        if ev:
            status = _get_val(ev, "status", "not_found")
            reason = _get_val(ev, "reason", "Not assessed")
            page_number = _get_val(ev, "page_number", None)
            quote = _get_val(ev, "quote", None)
        else:
            status = "not_found"
            reason = "Study or disclosure not identified in submitted document."
            page_number = None
            quote = None

        canonical_evals.append({
            "rule_id": rid,
            "rule_name": ref_rule["name"],
            "category": ref_rule["category"],
            "weight": ref_rule["weight"],
            "status": status,
            "reason": reason,
            "page_number": page_number,
            "quote": quote
        })

    def _compute_raw_score(evals: List[Dict[str, Any]], not_found_as_pass: bool = False) -> Tuple[int, int]:
        """Calculates score and critical fail count for a given evaluation set."""
        pts = 0.0
        crit_fails = 0

        for r in evals:
            w = r["weight"]
            st = r["status"]
            if st == "pass":
                pts += w * 1.0
            elif st == "partial":
                pts += w * 0.5
            elif st == "fail":
                pts += w * 0.0
                if r["category"] == "Critical":
                    crit_fails += 1
            elif st == "not_found":
                if not_found_as_pass:
                    pts += w * 1.0
                else:
                    pts += w * 0.0

        base_pct = (pts / total_weight) * 100.0

        # Apply hard caps for critical fails
        if crit_fails >= 2:
            capped_pct = min(base_pct, 40.0)
        elif crit_fails == 1:
            capped_pct = min(base_pct, 60.0)
        else:
            capped_pct = base_pct

        return round(capped_pct), crit_fails

    # 1. Base Score (range_low: not_found treated as fail)
    capped_score, crit_fails_count = _compute_raw_score(canonical_evals, not_found_as_pass=False)

    # 2. Upper Bound Score (range_high: not_found treated as pass)
    capped_score_high, _ = _compute_raw_score(canonical_evals, not_found_as_pass=True)

    # 3. Calculate Issue Penalties
    total_penalty = 0
    active_issues_count = 0
    for iss in issues:
        dec = _get_val(iss, "reviewer_decision", "Pending")
        if dec == "Dismissed":
            continue  # Dismissed issues are completely excluded from penalty

        active_issues_count += 1
        sev = _get_val(iss, "severity", "Major")
        if sev in ("Critical", "High"):
            total_penalty += 5
        elif sev in ("Major", "Medium"):
            total_penalty += 2

    # Final score and bounds after penalties
    final_score = max(0, min(100, capped_score - total_penalty))
    final_range_low = max(0, min(100, capped_score - total_penalty))
    final_range_high = max(final_range_low, min(100, capped_score_high - total_penalty))

    # 4. Band Determination
    if final_score >= 85:
        band = "High"
    elif final_score >= 65:
        band = "Moderate"
    elif final_score >= 40:
        band = "Low"
    else:
        band = "Very low"

    # 5. Counts per Category
    category_counts = {
        "Critical": {"pass": 0, "partial": 0, "fail": 0, "not_found": 0, "total": 0},
        "Major": {"pass": 0, "partial": 0, "fail": 0, "not_found": 0, "total": 0},
        "Minor": {"pass": 0, "partial": 0, "fail": 0, "not_found": 0, "total": 0},
    }
    status_totals = {"pass": 0, "partial": 0, "fail": 0, "not_found": 0}

    for r in canonical_evals:
        cat = r["category"]
        st = r["status"]
        if cat in category_counts:
            category_counts[cat]["total"] += 1
            if st in category_counts[cat]:
                category_counts[cat][st] += 1
        if st in status_totals:
            status_totals[st] += 1

    # 6. Top 3 Improvements Ranked by Potential Score Gain
    improvements = []
    for r in canonical_evals:
        if r["status"] == "pass":
            continue

        # Simulate changing this single rule to "pass"
        sim_evals = []
        for x in canonical_evals:
            if x["rule_id"] == r["rule_id"]:
                sim_evals.append({**x, "status": "pass"})
            else:
                sim_evals.append(x)

        sim_score, _ = _compute_raw_score(sim_evals, not_found_as_pass=False)
        sim_final = max(0, min(100, sim_score - total_penalty))
        gain = sim_final - final_score

        # If gain is 0 due to capping or penalties, fallback to theoretical base % gain
        weight_pts = (1.0 - (0.5 if r["status"] == "partial" else 0.0)) * r["weight"]
        theoretical_gain = round((weight_pts / total_weight) * 100)
        display_gain = max(gain, theoretical_gain)

        # Recommendation text
        if r["category"] == "Critical" and r["status"] == "fail":
            rec = f"Resolve critical deficiency in {r['rule_name']} to eliminate critical cap ({r['status'].upper()} -> PASS)."
        elif r["status"] == "not_found":
            rec = f"Include baseline chapter or disclosure for {r['rule_name']}."
        else:
            rec = f"Provide comprehensive data and mitigation annexures for {r['rule_name']}."

        improvements.append({
            "rule_id": r["rule_id"],
            "rule_name": r["rule_name"],
            "category": r["category"],
            "current_status": r["status"],
            "weight": r["weight"],
            "score_gain": display_gain,
            "actual_gain": gain,
            "recommendation": rec
        })

    # Sort improvements primarily by actual_gain, then score_gain, then weight
    improvements.sort(key=lambda x: (x["actual_gain"], x["score_gain"], x["weight"]), reverse=True)
    top_3_improvements = improvements[:3]

    return {
        "score": final_score,
        "band": band,
        "range_low": final_range_low,
        "range_high": final_range_high,
        "critical_fails": crit_fails_count,
        "total_penalty": total_penalty,
        "category_counts": category_counts,
        "status_totals": status_totals,
        "top_improvements": top_3_improvements,
        "canonical_evaluations": canonical_evals
    }
