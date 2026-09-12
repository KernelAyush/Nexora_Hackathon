"""
Minimal demo harness so the pipeline is clickable today.
P3 owns the real UI/UX - treat this as a working placeholder, not final.
"""

import streamlit as st
import os
import tempfile
from src.parser import parse_jd, parse_resume
from src.normalizer import normalize_resume
from src.jd_analyzer import analyze_jd
from src.ranking import rank_candidates
from src.explanations import top_n_explanations, answer_ranking_question
from src.bias_detector import analyze_jd_bias

st.set_page_config(page_title="Smart Shortlisting Engine", layout="wide")
st.title("Smart Shortlisting Engine")

jd_text = st.text_area("Paste the Job Description", height=200)
resume_files = st.file_uploader("Upload resumes (PDF)", type=["pdf"], accept_multiple_files=True)

if st.button("Run analysis") and jd_text and resume_files:
    with st.spinner("Parsing and scoring..."):
        jd_analysis = analyze_jd(parse_jd(jd_text))

        candidates = []
        for i, f in enumerate(resume_files, start=1):
            tmp_path = os.path.join(tempfile.gettempdir(), f.name)
            with open(tmp_path, "wb") as out:
                out.write(f.getbuffer())
            raw = parse_resume(tmp_path)
            candidates.append(normalize_resume(raw, candidate_id=f"candidate_{i:02d}", name=f.name))

        ranked = rank_candidates(jd_analysis, candidates)
        bias = analyze_jd_bias(jd_text, jd_analysis["required_skills"])

    st.session_state["ranked"] = ranked

    st.subheader("JD bias check")
    st.write(f"Severity: **{bias['severity']}** — {bias['explanation']}")
    for flag in bias["flags"]:
        st.write(f"- **{flag['type']}**: `{flag['term']}` — {flag['explanation']}")

    st.subheader("Ranking")
    st.dataframe([
        {"Rank": r["rank"], "Candidate": r["name"], "Final": r["final_score"],
         "Semantic": r["semantic_score"], "Keyword": r["keyword_score"]}
        for r in ranked
    ])

    st.subheader("Top 3 — why they ranked highly")
    for explanation in top_n_explanations(ranked, 3):
        st.text(explanation)
        st.divider()

if "ranked" in st.session_state:
    st.subheader("Ask the recruiter chat")
    question = st.text_input("e.g. 'Why is candidate_03 above candidate_07?'")
    if question:
        st.write(answer_ranking_question(question, st.session_state["ranked"]))
