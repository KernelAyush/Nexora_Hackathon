"""
schemas.py
==========
The shared data contract between P2 (this module's owner), P1 (matching/
ranking/scoring), and P3 (UI/chat). Nobody outside this file should need
to guess what a "candidate" or "jd" dict looks like — import the builder
functions below instead of hand-rolling dicts elsewhere in the codebase.

These are plain dicts (not classes) on purpose: fastest to pass around,
trivially JSON-serializable for caching/demo, and every teammate's AI
assistant can read a dict literal without extra explanation.
"""

from typing import List, Dict, Optional, TypedDict


class DateRange(TypedDict):
    start: str   # "YYYY-MM" or "unknown"
    end: str     # "YYYY-MM" or "present" or "unknown"
    raw: str     # original text, kept for debugging/explanations


class Candidate(TypedDict):
    id: str                      # e.g. "candidate_01" (derived from filename)
    name: str                    # best-guess human name, falls back to id
    source_file: str             # original filename
    raw_text: str                # untouched extracted PDF text
    normalized_text: str         # cleaned/whitespace-normalized full text
    sections: Dict[str, str]     # e.g. {"experience": "...", "skills": "...", "education": "...", "projects": "..."}
    skills: List[str]            # deduplicated, canonicalized skill names
    experience: List[str]        # bullet-ish lines pulled from the experience section
    education: List[str]         # lines pulled from the education section
    projects: List[str]          # lines pulled from the projects section
    dates: List[DateRange]       # every date range found anywhere in the resume
    parse_ok: bool                # False if this resume failed to parse cleanly
    parse_error: Optional[str]   # populated when parse_ok is False


class JobDescription(TypedDict):
    source_file: str
    raw_text: str
    normalized_text: str
    role_title: str
    required_skills: List[str]     # canonicalized
    preferred_skills: List[str]    # canonicalized
    experience_requirement: Optional[str]   # e.g. "0-1 years" (raw matched text)
    education_requirement: Optional[str]    # raw matched text, if any
    responsibilities: List[str]    # bullet-ish lines from a responsibilities/role section
    sections: Dict[str, str]


def empty_candidate(cand_id: str, source_file: str) -> Candidate:
    """Used when a resume fails to parse, so downstream code (P1's ranking
    loop) never has to special-case a missing candidate — it just sees
    parse_ok=False and can decide to skip/score-zero/flag it."""
    return {
        "id": cand_id,
        "name": cand_id,
        "source_file": source_file,
        "raw_text": "",
        "normalized_text": "",
        "sections": {},
        "skills": [],
        "experience": [],
        "education": [],
        "projects": [],
        "dates": [],
        "parse_ok": False,
        "parse_error": None,
    }
