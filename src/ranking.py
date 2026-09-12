"""
Combines keyword_score + semantic_score into one final ranking.

final_score = 0.5 * semantic_score + 0.5 * keyword_score

Weights are named constants so they can be retuned in five seconds against
the actual sample data without touching any other file.
"""

from src.matcher import keyword_score, semantic_score, prepare_batch

WEIGHT_SEMANTIC = 0.5
WEIGHT_KEYWORD = 0.5


def score_candidate(candidate: dict, jd_analysis: dict) -> dict:
    kw = keyword_score(candidate, jd_analysis)
    sem = semantic_score(candidate, jd_analysis)
    final = WEIGHT_SEMANTIC * sem["score"] + WEIGHT_KEYWORD * kw["score"]

    return {
        "candidate_id": candidate.get("id"),
        "name": candidate.get("name", ""),
        "final_score": round(final, 1),
        "semantic_score": sem["score"],
        "keyword_score": kw["score"],
        "matched_required": kw["matched_required"],
        "missing_required": kw["missing_required"],
        "matched_preferred": kw["matched_preferred"],
        "missing_preferred": kw["missing_preferred"],
        "semantic_evidence": sem["requirement_evidence"],
        "preferred_semantic_evidence": sem["preferred_evidence"],
        "score_breakdown": {
            "final_formula": f"{WEIGHT_SEMANTIC}*semantic + {WEIGHT_KEYWORD}*keyword",
            "semantic_formula": sem["formula"],
            "keyword_formula": kw["formula"],
            "semantic_backend": sem["backend"],
        },
    }


def rank_candidates(jd_analysis: dict, candidates: list) -> list:
    prepare_batch(jd_analysis, candidates)
    results = [score_candidate(c, jd_analysis) for c in candidates]
    results.sort(key=lambda r: r["final_score"], reverse=True)
    for i, r in enumerate(results, start=1):
        r["rank"] = i
    return results
