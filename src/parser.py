"""
parser.py
=========
PDF -> structured Candidate / JobDescription dicts (see schemas.py).

Design notes for P1 (read this before calling anything):
  - Every public function here is defensive: a single bad/scanned/corrupt
    PDF will never crash a batch run. Failures show up as
    candidate["parse_ok"] == False with candidate["parse_error"] set.
  - Text extraction uses pypdf first (fast); if a page yields no text
    pdfplumber is used as a fallback for that page (slower but sometimes
    recovers text pypdf misses).
"""

import os
import re
from typing import List, Optional

from pypdf import PdfReader
import pdfplumber

from normalizer import (
    clean_text,
    normalize_heading,
    extract_skills_from_text,
    find_all_dates,
)
from schemas import Candidate, JobDescription, empty_candidate


# ---------------------------------------------------------------------------
# 1. PDF TEXT EXTRACTION
# ---------------------------------------------------------------------------
def extract_pdf_text(path: str) -> str:
    """Extract all text from a PDF. Tries pypdf per page; falls back to
    pdfplumber for any page pypdf returns nothing useful for. Never raises
    -- returns whatever text it managed to get (possibly empty string)."""
    pages_text: List[str] = []
    pypdf_failed = False
    try:
        reader = PdfReader(path)
        for page in reader.pages:
            try:
                pages_text.append(page.extract_text() or "")
            except Exception:
                pages_text.append("")
    except Exception:
        pypdf_failed = True
        pages_text = []

    needs_fallback = pypdf_failed or all(not p.strip() for p in pages_text)
    if needs_fallback:
        try:
            fallback_pages = []
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    try:
                        fallback_pages.append(page.extract_text() or "")
                    except Exception:
                        fallback_pages.append("")
            if any(p.strip() for p in fallback_pages):
                pages_text = fallback_pages
        except Exception:
            pass  # keep whatever pages_text already has, even if empty

    return "\n".join(pages_text)


# ---------------------------------------------------------------------------
# 2. NAME GUESSING
# ---------------------------------------------------------------------------
def _guess_name(text: str, fallback: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if "@" in line or "http" in line.lower() or any(ch.isdigit() for ch in line):
            return fallback
        words = line.split()
        if 1 <= len(words) <= 4 and all(w[:1].isupper() for w in words):
            return line
        return fallback  # first non-empty line didn't look like a name
    return fallback


# ---------------------------------------------------------------------------
# 3. RESUME SECTION SPLITTING
# ---------------------------------------------------------------------------
def _looks_like_heading(line: str) -> bool:
    """Fallback heuristic for headings that aren't in our known list:
    short, no trailing sentence punctuation, mostly upper/title case."""
    stripped = line.strip().rstrip(":")
    if not stripped or len(stripped) > 40:
        return False
    if stripped.endswith(('.', ',')):
        return False
    if any(ch.isdigit() for ch in stripped):
        return False  # dates ("Jan 2024 - Present") and durations aren't headings
    words = stripped.split()
    if not (1 <= len(words) <= 5):
        return False
    return stripped.isupper() or stripped.istitle()


_CANONICAL_KEYS = {"experience", "education", "projects", "skills"}


def split_resume_sections(text: str) -> dict:
    """Returns {canonical_section: joined_text}. Unrecognized headings are
    kept under their own lowercase key so no content is silently dropped.

    Once we're inside a *known* canonical section, the fuzzy
    "looks like a heading" fallback is disabled -- only another exact,
    recognized header can end it. This matters because job-title lines
    like "Design Intern, Creative Studio" are short and title-cased just
    like a real heading, and would otherwise get misread as a new section
    and silently truncate the real one."""
    sections: dict = {}
    current_key = "header"  # anything before the first recognized heading
    buffer: List[str] = []

    def flush():
        if buffer:
            joined = "\n".join(buffer).strip()
            if joined:
                sections[current_key] = (sections.get(current_key, "") + "\n" + joined).strip()

    for line in text.splitlines():
        raw = line.strip()
        canon = normalize_heading(raw) if raw else None
        if canon:
            flush()
            buffer = []
            current_key = canon
            continue
        if current_key not in _CANONICAL_KEYS and _looks_like_heading(raw):
            flush()
            buffer = []
            current_key = raw.lower().rstrip(":")
            continue
        buffer.append(line)
    flush()
    return sections


def _lines_from_section(sections: dict, key: str) -> List[str]:
    text = sections.get(key, "")
    lines = [ln.strip(" -\u2022\t") for ln in text.splitlines()]
    return [ln for ln in lines if ln]


# ---------------------------------------------------------------------------
# 4. PUBLIC: PARSE ONE RESUME
# ---------------------------------------------------------------------------
def extract_resume(path: str) -> Candidate:
    return parse_resume(path)


def parse_resume(path: str) -> Candidate:
    cand_id = os.path.splitext(os.path.basename(path))[0]
    try:
        raw_text = extract_pdf_text(path)
        if not raw_text.strip():
            cand = empty_candidate(cand_id, os.path.basename(path))
            cand["parse_error"] = "No extractable text (possibly a scanned/image PDF)."
            return cand

        normalized_text = clean_text(raw_text)
        sections = split_resume_sections(normalized_text)
        name = _guess_name(normalized_text, fallback=cand_id)

        skills_from_skills_section = extract_skills_from_text(sections.get("skills", ""))
        skills_from_full_text = extract_skills_from_text(normalized_text)
        seen = set()
        skills = []
        for s in skills_from_skills_section + skills_from_full_text:
            if s not in seen:
                seen.add(s)
                skills.append(s)

        candidate: Candidate = {
            "id": cand_id,
            "name": name,
            "source_file": os.path.basename(path),
            "raw_text": raw_text,
            "normalized_text": normalized_text,
            "sections": sections,
            "skills": skills,
            "experience": _lines_from_section(sections, "experience"),
            "education": _lines_from_section(sections, "education"),
            "projects": _lines_from_section(sections, "projects"),
            "dates": find_all_dates(normalized_text),
            "parse_ok": True,
            "parse_error": None,
        }
        return candidate
    except Exception as e:
        cand = empty_candidate(cand_id, os.path.basename(path))
        cand["parse_error"] = f"{type(e).__name__}: {e}"
        return cand


# ---------------------------------------------------------------------------
# 5. PUBLIC: BATCH PROCESS RESUMES
# ---------------------------------------------------------------------------
def batch_process_resumes(paths: List[str]) -> List[Candidate]:
    candidates = [parse_resume(p) for p in paths]
    return sorted(candidates, key=lambda c: c["id"])


def process_all_resumes(resume_directory: str) -> List[Candidate]:
    paths = [
        os.path.join(resume_directory, f)
        for f in os.listdir(resume_directory)
        if f.lower().endswith(".pdf")
    ]
    return batch_process_resumes(paths)


# ---------------------------------------------------------------------------
# 6. JD PARSING
# ---------------------------------------------------------------------------
_REQUIRED_MARKERS = [
    "required skills", "requirements", "must have", "must-have",
    "minimum qualifications", "what you need", "you must have",
]
_PREFERRED_MARKERS = [
    "preferred", "nice to have", "nice-to-have", "good to have",
    "bonus points", "bonus", "a plus", "is a plus",
]
_RESPONSIBILITY_MARKERS = [
    "responsibilities", "what you'll do", "what you will do", "role overview", "key responsibilities",
]

_EXPERIENCE_REQ_RE = re.compile(
    r"(\d+\+?\s*(?:-\s*\d+)?\s*years?[^.\n]{0,80})", re.IGNORECASE
)
# Negative lookahead (?![a-zA-Z]) after each alternative stops the pattern
# from matching mid-word inside unrelated words -- e.g. without it,
# "b.?e.?" matches the "Be" inside "Bengaluru" and swallows the rest of
# that sentence as a bogus "education requirement".
# Case-insensitive: for unambiguous multi-letter terms that don't collide
# with ordinary English words.
_EDUCATION_REQ_RE = re.compile(
    r"((?:bachelor(?![a-zA-Z])|b\.?tech(?![a-zA-Z])|"
    r"master(?![a-zA-Z])|m\.?tech(?![a-zA-Z])|degree(?![a-zA-Z]))[^.\n]{0,60})",
    re.IGNORECASE,
)
# Case-SENSITIVE: "B.E."/"BE"/"M.E."/"ME" as bare 2-letter degree
# abbreviations are indistinguishable from the common words "be"/"me" once
# lowercased, so these only match when written in caps, as real resumes do
# (e.g. "B.E Computer Science", "BE Mechanical") -- never against lowercase
# prose like "...and be comfortable working...".
_EDUCATION_REQ_RE_CASESENSITIVE = re.compile(
    r"((?:B\.?E\.?|M\.?E\.?)(?![a-zA-Z])[^.\n]{0,60})"
)

# Headings that typically follow a responsibilities section in a JD --
# used only to bound where the responsibilities slice ends, so unrelated
# trailing content ("What We Offer", "Benefits", ...) doesn't get folded
# into the responsibilities list.
_TRAILING_SECTION_MARKERS = [
    "what we offer", "benefits", "perks", "compensation", "salary",
    "how to apply", "about the company", "about us", "equal opportunity",
]


def _find_marker_span(text_lower: str, markers: List[str]) -> Optional[int]:
    positions = [text_lower.find(m) for m in markers if m in text_lower]
    return min(positions) if positions else None


def _slice_after(text: str, start: Optional[int], all_starts: List[int]) -> str:
    if start is None:
        return ""
    later = [s for s in all_starts if s > start]
    end = min(later) if later else len(text)
    return text[start:end]


def extract_jd(path: str) -> JobDescription:
    return parse_jd(path)


def parse_jd(path: str) -> JobDescription:
    if path.lower().endswith(".pdf"):
        raw_text = extract_pdf_text(path)
    else:
        with open(path, "r", encoding="utf-8") as f:
            raw_text = f.read()

    normalized_text = clean_text(raw_text)
    lowered = normalized_text.lower()
    sections = split_resume_sections(normalized_text)  # header-detection logic is reusable

    req_start = _find_marker_span(lowered, _REQUIRED_MARKERS)
    pref_start = _find_marker_span(lowered, _PREFERRED_MARKERS)
    resp_start = _find_marker_span(lowered, _RESPONSIBILITY_MARKERS)
    trailing_start = _find_marker_span(lowered, _TRAILING_SECTION_MARKERS)
    all_starts = [s for s in (req_start, pref_start, resp_start) if s is not None]
    # trailing_start only bounds slices (e.g. stops "responsibilities" from
    # running into "what we offer") -- it isn't itself extracted as a block.
    all_starts_with_trailing = all_starts + ([trailing_start] if trailing_start is not None else [])

    required_block = _slice_after(normalized_text, req_start, all_starts_with_trailing)
    preferred_block = _slice_after(normalized_text, pref_start, all_starts_with_trailing)
    responsibilities_block = _slice_after(normalized_text, resp_start, all_starts_with_trailing)

    required_skills = extract_skills_from_text(required_block) if required_block else []
    preferred_skills = extract_skills_from_text(preferred_block) if preferred_block else []

    if not required_skills and not preferred_skills:
        required_skills = extract_skills_from_text(normalized_text)
    else:
        all_mentioned = extract_skills_from_text(normalized_text)
        already = set(required_skills) | set(preferred_skills)
        required_skills += [s for s in all_mentioned if s not in already]

    exp_match = _EXPERIENCE_REQ_RE.search(normalized_text)
    # Try the unambiguous case-insensitive terms first (bachelor/master/
    # degree/b.tech/m.tech); only fall back to the case-sensitive bare
    # "B.E."/"M.E." check if none of those were found.
    edu_match = _EDUCATION_REQ_RE.search(normalized_text) or \
        _EDUCATION_REQ_RE_CASESENSITIVE.search(normalized_text)

    role_title = ""
    for line in normalized_text.splitlines():
        if line.strip():
            role_title = line.strip()
            break

    jd: JobDescription = {
        "source_file": os.path.basename(path),
        "raw_text": raw_text,
        "normalized_text": normalized_text,
        "role_title": role_title,
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "experience_requirement": exp_match.group(1).strip() if exp_match else None,
        "education_requirement": edu_match.group(1).strip() if edu_match else None,
        "responsibilities": [
            ln.strip(" -\u2022\t") for ln in responsibilities_block.splitlines() if ln.strip()
        ],
        "sections": sections,
    }
    return jd


# ---------------------------------------------------------------------------
# 7. DEBUG OUTPUT
# ---------------------------------------------------------------------------
def debug_print_candidate(c: Candidate) -> None:
    print(f"{c['id']}  ({c['name']})")
    print(f"  Parsed OK: {'YES' if c['parse_ok'] else 'NO - ' + str(c['parse_error'])}")
    if c["parse_ok"]:
        print(f"  Skills: {', '.join(c['skills']) if c['skills'] else '(none found)'}")
        print(f"  Experience lines: {len(c['experience'])}")
        print(f"  Projects lines: {len(c['projects'])}")
        print(f"  Education lines: {len(c['education'])}")
        print(f"  Dates found: {c['dates']}")
    print()
