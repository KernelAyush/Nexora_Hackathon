"""
Run before every demo: python tests/smoke_test.py
Uses synthetic candidates so it doesn't depend on P2's parser being done.
If this doesn't pass clean, don't touch app.py until it does.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.jd_analyzer import analyze_jd
from src.ranking import rank_candidates
from src.explanations import top_n_explanations, answer_ranking_question
from src.bias_detector import analyze_jd_bias
from src.schemas import empty_candidate

JD_TEXT = """
We are hiring an aggressive rockstar Backend Engineer with 10+ years experience.

Required Skills:
Node.js, Express, MongoDB, REST API, Git

Preferred:
AWS, Docker, TypeScript
"""


def make_candidate(cid, name, skills, experience):
    c = empty_candidate(cid, name)
    c["skills"] = skills
    c["experience"] = experience
    c["normalized_text"] = (" ".join(skills) + " " + " ".join(experience)).lower()
    c["raw_text"] = c["normalized_text"]
    return c


candidates = [
    make_candidate(
        "candidate_01", "Strong Fit", ["node.js", "express", "mongodb", "git"],
        ["Built REST APIs using Express and MongoDB for a fintech startup."],
    ),
    make_candidate(
        "candidate_02", "Partial Fit", ["python", "django", "postgresql"],
        ["Built Django web apps with PostgreSQL for an e-commerce company."],
    ),
    make_candidate(
        "candidate_03", "Weak Fit", ["java", "spring"],
        ["Enterprise Java development with Spring Boot for a bank."],
    ),
]

if __name__ == "__main__":
    jd_analysis = analyze_jd(JD_TEXT)
    print("JD analysis:", jd_analysis)
    assert jd_analysis["required_skills"], "required skills should not be empty"
    assert "aws" in jd_analysis["preferred_skills"], "aws should land in preferred, not required"

    ranked = rank_candidates(jd_analysis, candidates)
    print("\n--- Ranking ---")
    for r in ranked:
        print(r["rank"], r["candidate_id"], "final:", r["final_score"],
              "semantic:", r["semantic_score"], "keyword:", r["keyword_score"])
    assert ranked[0]["candidate_id"] == "candidate_01", "strongest fit should rank #1"

    print("\n--- Top 3 explanations ---")
    for e in top_n_explanations(ranked):
        print(e, "\n")

    bias = analyze_jd_bias(JD_TEXT, jd_analysis["required_skills"])
    print("--- Bias check ---")
    print(bias)
    assert bias["severity"] != "none", "the synthetic JD has deliberate bias flags to catch"

    print("\n--- Chat ---")
    print(answer_ranking_question("why is candidate_01 above candidate_03", ranked))
    print(answer_ranking_question("what skills is candidate_02 missing", ranked))
    print(answer_ranking_question("why isn't candidate_03 in the top 3", ranked))

    print("\nSMOKE TEST PASSED")
