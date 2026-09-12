"""
THE SHARED DATA CONTRACT. Read this before writing any integration code.

We use plain dicts, not classes - zero setup cost for P2/P3, easy to print,
easy to json.dumps for debugging, easy to feed into Streamlit directly.
"""

REQUIRED_CANDIDATE_FIELDS = [
    "id", "name", "raw_text", "normalized_text",
    "skills", "experience", "education", "projects",
]


def empty_candidate(candidate_id: str, name: str = "") -> dict:
    """P2: start from this and fill it in. Every field must exist even if
    empty - the matcher assumes the keys are present."""
    return {
        "id": candidate_id,
        "name": name,
        "raw_text": "",          # full extracted text, unmodified
        "normalized_text": "",   # lowercased / whitespace-cleaned full text
        "skills": [],            # list[str] - explicit skills you detected (best effort is fine)
        "experience": [],        # list[str] - one entry per role/bullet, free text
        "education": [],         # list[str]
        "projects": [],          # list[str]
    }


def validate_candidate(candidate: dict) -> list:
    """Returns a list of problems (empty = valid). Never raises - a bad
    candidate should degrade gracefully, not crash the whole ranking run."""
    problems = []
    for field in REQUIRED_CANDIDATE_FIELDS:
        if field not in candidate:
            problems.append(f"missing field: {field}")
    if not candidate.get("normalized_text") and not candidate.get("raw_text"):
        problems.append("no text at all (raw_text and normalized_text both empty)")
    return problems


def empty_jd() -> dict:
    return {"raw_text": ""}


# ---------------------------------------------------------------------------
# OUTPUT CONTRACT - what rank_candidates() hands back. This is the ONLY
# structure P3 needs for the table, the top-3 cards, and the chat function.
# ---------------------------------------------------------------------------
#
# rank_candidates(jd_analysis, candidates) -> list[dict], sorted best-first:
#
# {
#   "rank": 1,
#   "candidate_id": "candidate_07",
#   "name": "resume7.pdf",
#   "final_score": 91.4,
#   "semantic_score": 93.2,
#   "keyword_score": 89.7,
#   "matched_required": ["react", "node.js"],
#   "missing_required": ["aws"],
#   "matched_preferred": ["docker"],
#   "missing_preferred": [],
#   "semantic_evidence": [
#       {"requirement": "node.js", "score": 0.81, "snippet": "Built REST APIs..."}
#   ],
#   "preferred_semantic_evidence": [...],
#   "score_breakdown": {
#       "final_formula": "0.5*semantic + 0.5*keyword",
#       "semantic_formula": "...",
#       "keyword_formula": "...",
#       "semantic_backend": "sentence-transformers/all-MiniLM-L6-v2" (or tfidf-fallback),
#   },
# }
