"""
Deterministic and analytical tools available to the Multi-Agent Review Pipeline.
Used by Specialists and Verifier for Thought/Action/Observation loops.
"""
import re
from typing import Dict, List, Any, Optional

EC_CHECKLIST = [
    "project description",
    "EIA report",
    "EMP",
    "baseline data",
    "public hearing",
    "biodiversity study",
    "water and air quality data",
    "land use details"
]

CHECKLIST_KEYWORDS: Dict[str, List[str]] = {
    "project description": ["project description", "project name", "proponent", "capacity", "project background"],
    "EIA report": ["eia", "environmental impact assessment", "impact assessment", "terms of reference", "tor"],
    "EMP": ["emp", "environmental management plan", "mitigation measures", "monitoring plan"],
    "baseline data": ["baseline", "monitoring period", "ambient air", "baseline environmental", "meteorology"],
    "public hearing": ["public hearing", "public consultation", "minutes of the hearing", "stakeholder"],
    "biodiversity study": ["biodiversity", "flora and fauna", "wildlife sanctuary", "ecological survey", "endangered", "forest"],
    "water and air quality data": ["air quality", "water quality", "pm10", "pm2.5", "water balance", "effluent", "ambient noise"],
    "land use details": ["land use", "hectares", "greenbelt", "land requirement", "demarcation", "topography"]
}


def parse_document_pages(text: str) -> Dict[int, str]:
    """Splits full extracted text into a dictionary of {page_num: page_content}."""
    pages = {}
    pattern = r"---\s*Page\s*(\d+)\s*---"
    parts = re.split(pattern, text)
    
    # If standard delimiters exist
    if len(parts) > 1:
        # parts[0] is preamble, then alternating (page_num, page_text)
        for i in range(1, len(parts), 2):
            try:
                p_num = int(parts[i])
                p_text = parts[i + 1].strip()
                pages[p_num] = p_text
            except (ValueError, IndexError):
                continue
    else:
        # Fallback single page
        pages[1] = text.strip()
    return pages


def search_document_text(query: str, text: str) -> List[Dict[str, Any]]:
    """
    Tool: Searches for keyword or phrase matches across document pages.
    Returns list of matches with page numbers and surrounding context snippet.
    """
    pages = parse_document_pages(text)
    clean_query = query.strip().lower()
    matches = []
    
    for page_num, page_content in pages.items():
        lines = page_content.splitlines()
        for idx, line in enumerate(lines):
            if clean_query in line.lower():
                # Grab surrounding lines for context
                start_l = max(0, idx - 1)
                end_l = min(len(lines), idx + 2)
                snippet = " ".join(l.strip() for l in lines[start_l:end_l] if l.strip())
                matches.append({
                    "page": page_num,
                    "query": query,
                    "snippet": snippet[:250]
                })
    return matches


def extract_page_content(page_num: int, text: str) -> Dict[str, Any]:
    """
    Tool: Extracts full text of a specific page number.
    """
    pages = parse_document_pages(text)
    content = pages.get(page_num, "")
    if content:
        return {"page": page_num, "found": True, "text": content}
    return {"page": page_num, "found": False, "text": f"Page {page_num} not found in document (available pages: {list(pages.keys())})"}


def get_checklist_status(checklist_item: str, text: str) -> Dict[str, Any]:
    """
    Tool: Evaluates presence of a mandatory checklist study.
    Returns whether found, matched keywords, and citing page numbers.
    """
    item_clean = checklist_item.strip().lower()
    keywords = CHECKLIST_KEYWORDS.get(item_clean, [item_clean])
    pages = parse_document_pages(text)
    
    found_pages = []
    matched_snippets = []
    
    for page_num, content in pages.items():
        content_lower = content.lower()
        for kw in keywords:
            if kw in content_lower:
                if page_num not in found_pages:
                    found_pages.append(page_num)
                # Find matching snippet
                for line in content.splitlines():
                    if kw in line.lower():
                        matched_snippets.append(line.strip())
                        break
                break
                
    is_present = len(found_pages) > 0
    return {
        "checklist_item": checklist_item,
        "is_present": is_present,
        "pages_found": found_pages,
        "sample_evidence": matched_snippets[:3] if is_present else None
    }


def find_numeric_mentions(metric_name: str, text: str) -> List[Dict[str, Any]]:
    """
    Tool: Extracts numeric values and measurement units related to a specified metric
    (e.g., 'water', 'land', 'capacity', 'stack', 'emission', 'cost', 'greenbelt').
    """
    pages = parse_document_pages(text)
    metric_clean = metric_name.strip().lower()
    results = []
    
    # Common pattern: numbers with commas/decimals followed by or near units
    num_pattern = re.compile(r"(\d+(?:,\d+)*(?:\.\d+)?)\s*(kld|m3/day|mld|ha|hectares|acres|mw|tpd|tpa|m|meters|mg/nm3|kld|inr|crores?|%|percent)?", re.IGNORECASE)
    
    for page_num, content in pages.items():
        for line in content.splitlines():
            if metric_clean in line.lower():
                matches = num_pattern.findall(line)
                for val, unit in matches:
                    if val:
                        results.append({
                            "page": page_num,
                            "metric": metric_name,
                            "value": val,
                            "unit": unit or "unspecified",
                            "context": line.strip()[:180]
                        })
    return results


def verify_citation(page_ref: str, evidence_quote: str, text: str) -> Dict[str, Any]:
    """
    Tool used by Verifier: Checks if a cited quote or number actually exists
    in the referenced page text.
    """
    pages = parse_document_pages(text)
    
    # Parse target pages from page_ref (e.g., 'Page 2', 'Page 1 vs Page 2', 'Full Document')
    if not page_ref or "full document" in page_ref.lower():
        # Check globally
        target_pages = list(pages.keys())
    else:
        page_nums = [int(p) for p in re.findall(r"\b(\d+)\b", page_ref)]
        target_pages = page_nums if page_nums else list(pages.keys())
        
    quote_clean = evidence_quote.strip().lower()
    # Normalize spaces and punctuation
    quote_words = set(re.findall(r"\b\w{3,}\b", quote_clean))

    # 1. Check inner quoted fragments if present (e.g. 'fresh water...' or "Daily Fresh...")
    inner_quotes = re.findall(r"['\"]([^'\"]{8,})['\"]", evidence_quote)
    if inner_quotes:
        inner_verified = 0
        for iq in inner_quotes:
            iq_clean = iq.strip().lower()
            if any(iq_clean in pages.get(p, "").lower() for p in target_pages):
                inner_verified += 1
        if inner_verified > 0:
            return {
                "verified": True,
                "confidence": 1.0,
                "matched_page": target_pages[0] if target_pages else 1,
                "reason": f"Verified {inner_verified} quoted citation(s) across target pages {target_pages}."
            }

    # 2. Check exact full quote across target pages
    for p_num in target_pages:
        p_text_lower = pages.get(p_num, "").lower()
        if quote_clean and quote_clean in p_text_lower:
            return {
                "verified": True,
                "confidence": 1.0,
                "matched_page": p_num,
                "reason": f"Exact quote verified on Page {p_num}."
            }

    # 3. Check combined target pages text (for cross-page comparisons like Page 1 vs Page 2)
    combined_target_text = " ".join(pages.get(p, "") for p in target_pages)
    combined_words = set(re.findall(r"\b\w{3,}\b", combined_target_text.lower()))

    if quote_words:
        combined_overlap = len(quote_words & combined_words) / float(len(quote_words))
        if combined_overlap >= 0.40:
            return {
                "verified": True,
                "confidence": round(combined_overlap, 2),
                "matched_page": target_pages[0] if target_pages else 1,
                "reason": f"Substantive evidence match ({int(combined_overlap * 100)}% term overlap) substantiated across {page_ref}."
            }

    # 4. Check individual page sentence overlap
    best_match_page = None
    best_overlap = 0.0
    matched_sentence = ""

    for p_num in target_pages:
        p_text = pages.get(p_num, "")
        for sentence in re.split(r"[.\n]", p_text):
            s_words = set(re.findall(r"\b\w{3,}\b", sentence.lower()))
            if not quote_words:
                continue
            overlap = len(quote_words & s_words) / float(len(quote_words))
            if overlap > best_overlap:
                best_overlap = overlap
                best_match_page = p_num
                matched_sentence = sentence.strip()

    if best_overlap >= 0.40:
        return {
            "verified": True,
            "confidence": round(best_overlap, 2),
            "matched_page": best_match_page,
            "reason": f"Substantive evidence match ({int(best_overlap*100)}% overlap) verified on Page {best_match_page}: '{matched_sentence[:100]}'."
        }

    return {
        "verified": False,
        "confidence": round(best_overlap, 2),
        "matched_page": best_match_page,
        "reason": f"Citation could not be substantiated on {page_ref} (best match overlap {int(best_overlap*100)}%)."
    }
