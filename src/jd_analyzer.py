"""
Extracts required/preferred skills from a raw JD string.

Heuristic, not ML: look for section headers to split "required" vs
"preferred" text, then run the shared skill taxonomy over each part.
If no clear headers exist, everything detected counts as required -
safer than letting a real requirement silently fall into "preferred"
and get under-weighted.
"""

import re
from src.skills_taxonomy import extract_skills_from_text

REQUIRED_HEADERS = [
    "required skills", "requirements", "must have", "must-have",
    "mandatory", "minimum qualifications", "you must have",
]
PREFERRED_HEADERS = [
    "preferred", "nice to have", "nice-to-have", "good to have",
    "bonus", "desirable", "would be a plus",
]

_HEADER_PATTERN = re.compile(
    r"(" + "|".join(re.escape(h) for h in REQUIRED_HEADERS + PREFERRED_HEADERS) + r")",
    re.IGNORECASE,
)


def split_required_preferred(jd_text: str):
    """Return (required_text, preferred_text)."""
    matches = list(_HEADER_PATTERN.finditer(jd_text))
    if not matches:
        return jd_text, ""

    required_chunks, preferred_chunks = [], []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(jd_text)
        chunk = jd_text[start:end]
        header = m.group(1).lower()
        if header in PREFERRED_HEADERS:
            preferred_chunks.append(chunk)
        else:
            required_chunks.append(chunk)

    # text before the first header is context, treat it as required
    required_text = jd_text[: matches[0].start()] + " " + " ".join(required_chunks)
    preferred_text = " ".join(preferred_chunks)
    return required_text, preferred_text


def analyze_jd(jd_text: str) -> dict:
    required_text, preferred_text = split_required_preferred(jd_text)
    required_skills = extract_skills_from_text(required_text)
    preferred_skills = extract_skills_from_text(preferred_text) - required_skills
    return {
        "raw_text": jd_text,
        "required_skills": sorted(required_skills),
        "preferred_skills": sorted(preferred_skills),
    }
