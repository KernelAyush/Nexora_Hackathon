"""
Turns structured ranking data into plain-English text. No LLM is required
for correctness - every sentence here is templated straight from real
scores/evidence, so the explanation can never contradict the score.

An LLM can optionally be layered on top purely to smooth the prose (see
polish_with_llm) - it never gets to invent facts or recompute anything.
"""

import re


def _skill_list(skills: list) -> str:
    return ", ".join(skills) if skills else "none"


def explain_candidate(result: dict) -> str:
    lines = [
        f"{result.get('name') or result['candidate_id']} — {result['final_score']} "
        f"(semantic {result['semantic_score']}, keyword {result['keyword_score']})",
        "",
        "Why ranked highly:",
    ]
    if result["matched_required"]:
        lines.append(f"- Matched required skills: {_skill_list(result['matched_required'])}")
    if result["matched_preferred"]:
        lines.append(f"- Matched preferred skills: {_skill_list(result['matched_preferred'])}")
    for e in result.get("semantic_evidence", []):
        if e["score"] >= 0.45:
            lines.append(
                f"- Strong semantic match for '{e['requirement']}' "
                f"(similarity {e['score']}): \"{e['snippet']}\""
            )
    lines.append("")
    lines.append("Missing / unclear:")
    if result["missing_required"]:
        lines.append(f"- Missing required: {_skill_list(result['missing_required'])}")
    if result["missing_preferred"]:
        lines.append(f"- Missing preferred: {_skill_list(result['missing_preferred'])}")
    if not result["missing_required"] and not result["missing_preferred"]:
        lines.append("- No clear gaps against the JD's detected skill list")
    return "\n".join(lines)


def top_n_explanations(ranked_results: list, n: int = 3) -> list:
    return [explain_candidate(r) for r in ranked_results[:n]]


def polish_with_llm(explanation_text: str, llm_call_fn=None) -> str:
    """Optional: pass a callable(str) -> str wrapping any LLM to turn the
    bullets into flowing prose. If llm_call_fn is None, the templated text
    is returned unchanged - the app must work with zero API keys configured."""
    if llm_call_fn is None:
        return explanation_text
    try:
        return llm_call_fn(
            "Rewrite the following recruiter notes as 3-4 natural sentences. "
            "Do not add any facts, skills, or numbers not already present:\n\n"
            + explanation_text
        )
    except Exception:
        return explanation_text


# ------------------------------ recruiter chat -------------------------------

def _find_candidate(token: str, ranked_results: list):
    """Resolve a 'Candidate X' reference: exact id, id containing the token,
    then name containing the token."""
    q = token.strip().lower()
    for r in ranked_results:
        if r["candidate_id"].lower() == q:
            return r
    for r in ranked_results:
        if q and q in r["candidate_id"].lower():
            return r
    for r in ranked_results:
        if r.get("name") and q in r["name"].lower():
            return r
    return None


def answer_ranking_question(question: str, ranked_results: list) -> str:
    """Rule-based Q&A over the ranking output. Never recalculates scores -
    only reads and formats what rank_candidates() already produced."""
    q = question.lower().strip()

    # "why is candidate X above/below candidate Y"
    m = re.search(
        r"candidate\s*([a-z0-9_]+).*?(above|below|higher|lower).*?candidate\s*([a-z0-9_]+)", q
    )
    if m:
        a = _find_candidate(m.group(1), ranked_results)
        b = _find_candidate(m.group(3), ranked_results)
        if a and b:
            higher, lower = (a, b) if a["final_score"] >= b["final_score"] else (b, a)
            sem_gap = higher["semantic_score"] - lower["semantic_score"]
            kw_gap = higher["keyword_score"] - lower["keyword_score"]
            driver = "keyword coverage" if kw_gap > sem_gap else "semantic relevance"
            missing_note = _skill_list(lower["missing_required"]) or "no required skills, but scored lower overall"
            return (
                f"{higher.get('name') or higher['candidate_id']} (rank {higher['rank']}, "
                f"{higher['final_score']}) scores above "
                f"{lower.get('name') or lower['candidate_id']} (rank {lower['rank']}, "
                f"{lower['final_score']}) mainly due to {driver}: it matched "
                f"{_skill_list(higher['matched_required'])} where the other candidate was missing "
                f"{missing_note}."
            )
        return "I couldn't find one or both of those candidates in the current ranking."

    m = re.search(r"candidate\s*([a-z0-9_]+)", q)

    # "why isn't candidate X in the top 3"
    if ("top 3" in q or "top three" in q) and m:
        c = _find_candidate(m.group(1), ranked_results)
        if c:
            if c["rank"] <= 3:
                return f"{c.get('name') or c['candidate_id']} is actually rank {c['rank']}."
            third = ranked_results[2]
            return (
                f"{c.get('name') or c['candidate_id']} is rank {c['rank']} with score "
                f"{c['final_score']}, below #3 ({third.get('name') or third['candidate_id']}, "
                f"{third['final_score']}). Missing required skills: "
                f"{_skill_list(c['missing_required']) or 'none - the gap is mostly semantic relevance'}."
            )

    # "what skills is candidate X missing"
    if "missing" in q and m:
        c = _find_candidate(m.group(1), ranked_results)
        if c:
            return (
                f"{c.get('name') or c['candidate_id']} is missing required: "
                f"{_skill_list(c['missing_required'])}; missing preferred: "
                f"{_skill_list(c['missing_preferred'])}."
            )

    # "which candidate has the strongest X experience"
    m2 = re.search(r"strongest\s+([a-z0-9\.\+# ]+?)\s*(experience|skills?)?$", q)
    if m2:
        skill = m2.group(1).strip()
        best, best_score = None, -1.0
        for r in ranked_results:
            for e in r.get("semantic_evidence", []):
                if skill in e["requirement"].lower() and e["score"] > best_score:
                    best, best_score = r, e["score"]
        if best:
            return (
                f"{best.get('name') or best['candidate_id']} has the strongest match for "
                f"'{skill}' (similarity {best_score}, overall rank {best['rank']})."
            )
        return f"I couldn't find strong evidence for '{skill}' in the current ranking."

    return (
        "I can answer questions like 'why is candidate X above candidate Y', "
        "'why isn't candidate X in the top 3', 'what skills is candidate X missing', "
        "or 'which candidate has the strongest <skill> experience'."
    )
