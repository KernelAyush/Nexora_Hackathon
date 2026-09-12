"""
normalizer.py
=============
Turns messy, inconsistent resume text into consistent tokens:
  - skill name variants -> one canonical name          (ReactJS/React.js -> React)
  - section header variants -> one canonical section   (Professional Experience -> experience)
  - loose date strings -> {start, end, raw}             (Jan 2024 - Present -> {"2024-01","present"})
  - whitespace/bullet noise -> cleaned text

Kept deliberately dependency-light (stdlib `difflib` for fuzzy matching
against a *small known vocabulary only* — never against every word in
the resume, which would be slow and would produce garbage matches).
"""

import re
import difflib
from typing import Optional, List, Dict

# ---------------------------------------------------------------------------
# 1. SKILL ALIASES
# ---------------------------------------------------------------------------
# canonical -> list of surface forms (lowercase, as they'd realistically
# appear in a resume, including common typo/spacing variants).
SKILL_ALIASES: Dict[str, List[str]] = {
    "JavaScript": ["javascript", "java script", "js", "es6", "ecmascript"],
    "TypeScript": ["typescript", "type script", "ts"],
    "Python": ["python", "python3", "py"],
    "Java": ["java"],
    "C++": ["c++", "cpp", "c plus plus"],
    "C#": ["c#", "csharp", "c-sharp"],
    "Node.js": ["node.js", "nodejs", "node js", "node"],
    "Express": ["express.js", "expressjs", "express js", "express"],
    "React": ["react.js", "reactjs", "react js", "react"],
    "Next.js": ["next.js", "nextjs", "next js"],
    "Angular": ["angular.js", "angularjs", "angular"],
    "Vue": ["vue.js", "vuejs", "vue"],
    "Redux": ["redux"],
    "HTML": ["html5", "html"],
    "CSS": ["css3", "css", "sass", "scss", "tailwind", "tailwindcss", "bootstrap"],
    "REST API": ["rest api", "restful api", "restful", "rest apis", "api development"],
    "GraphQL": ["graphql"],
    "Django": ["django"],
    "Flask": ["flask"],
    "FastAPI": ["fastapi", "fast api"],
    "Spring Boot": ["spring boot", "springboot", "spring"],
    "SQL": ["sql", "structured query language"],
    "MySQL": ["mysql", "my sql"],
    "PostgreSQL": ["postgresql", "postgres", "postgre sql"],
    "MongoDB": ["mongodb", "mongo db", "mongo"],
    "Firebase": ["firebase"],
    "Redis": ["redis"],
    "Git": ["git", "github", "gitlab", "version control"],
    "Docker": ["docker", "containerization"],
    "Kubernetes": ["kubernetes", "k8s"],
    "AWS": ["aws", "amazon web services", "ec2", "s3"],
    "Azure": ["azure", "microsoft azure"],
    "GCP": ["gcp", "google cloud", "google cloud platform"],
    "CI/CD": ["ci/cd", "cicd", "continuous integration", "jenkins", "github actions"],
    "Linux": ["linux", "unix", "bash", "shell scripting"],
    "Machine Learning": ["machine learning", "ml"],
    "Deep Learning": ["deep learning", "neural networks"],
    "Pandas": ["pandas"],
    "NumPy": ["numpy"],
    "TensorFlow": ["tensorflow"],
    "PyTorch": ["pytorch"],
    "Android": ["android", "kotlin"],
    "iOS": ["ios", "swift", "swiftui"],
    "Flutter": ["flutter", "dart"],
    "React Native": ["react native"],
    "Data Structures & Algorithms": ["data structures", "dsa", "algorithms"],
    "OOP": ["oop", "object oriented programming", "object-oriented programming"],
}

# lowercase surface-form -> canonical, built once at import time
_ALIAS_TO_CANON: Dict[str, str] = {}
for canon, aliases in SKILL_ALIASES.items():
    for a in aliases:
        _ALIAS_TO_CANON[a] = canon

_KNOWN_SURFACE_FORMS = list(_ALIAS_TO_CANON.keys())


def normalize_skill(skill: str) -> Optional[str]:
    """Map a raw skill token/phrase to its canonical name.
    Returns None if it doesn't resemble any known skill closely enough
    (so callers can decide to drop it rather than silently mis-map it).
    """
    if not skill:
        return None
    key = re.sub(r"[.\-_]", " ", skill.strip().lower())
    key = re.sub(r"\s+", " ", key).strip()

    if key in _ALIAS_TO_CANON:
        return _ALIAS_TO_CANON[key]

    # lightweight typo tolerance: only fuzzy-match against the small known
    # vocabulary, never against arbitrary resume text (keeps it fast and
    # avoids nonsense matches).
    close = difflib.get_close_matches(key, _KNOWN_SURFACE_FORMS, n=1, cutoff=0.84)
    if close:
        return _ALIAS_TO_CANON[close[0]]
    return None


def extract_skills_from_text(text: str) -> List[str]:
    """Scan free text for any known skill surface form (substring match,
    longest-alias-first so 'react native' isn't swallowed by 'react').
    Returns deduplicated canonical names in first-seen order."""
    if not text:
        return []
    lowered = re.sub(r"\s+", " ", text.lower())
    found = []
    seen = set()
    for alias in sorted(_KNOWN_SURFACE_FORMS, key=len, reverse=True):
        pattern = r"(?<![a-z0-9+#.])" + re.escape(alias) + r"(?![a-z0-9])"
        if re.search(pattern, lowered):
            canon = _ALIAS_TO_CANON[alias]
            if canon not in seen:
                seen.add(canon)
                found.append(canon)
    return found


# ---------------------------------------------------------------------------
# 2. SECTION HEADER NORMALIZATION
# ---------------------------------------------------------------------------
SECTION_HEADER_MAP: Dict[str, List[str]] = {
    "experience": [
        "work experience", "professional experience", "employment history",
        "experience", "internships", "internship experience", "work history",
    ],
    "education": [
        "education", "academic background", "academic qualifications",
        "qualifications", "educational background",
    ],
    "projects": [
        "projects", "academic projects", "personal projects", "key projects",
        "project experience",
    ],
    "skills": [
        "technical skills", "skills", "technologies", "technical expertise",
        "core competencies", "skill set",
    ],
}
_HEADER_TO_CANON: Dict[str, str] = {}
for canon, variants in SECTION_HEADER_MAP.items():
    for v in variants:
        _HEADER_TO_CANON[v] = canon


def normalize_heading(raw_heading: str) -> Optional[str]:
    key = raw_heading.strip().lower().rstrip(":")
    key = re.sub(r"\s+", " ", key)
    return _HEADER_TO_CANON.get(key)


# ---------------------------------------------------------------------------
# 3. DATE NORMALIZATION
# ---------------------------------------------------------------------------
_MONTHS = {
    "jan": "01", "january": "01", "feb": "02", "february": "02",
    "mar": "03", "march": "03", "apr": "04", "april": "04",
    "may": "05", "jun": "06", "june": "06", "jul": "07", "july": "07",
    "aug": "08", "august": "08", "sep": "09", "sept": "09", "september": "09",
    "oct": "10", "october": "10", "nov": "11", "november": "11",
    "dec": "12", "december": "12",
}

# Matches: "Jan 2024", "January 2024", "01/2024", "2024"
# Month word is restricted to real month names/abbreviations (not any
# 3-9 letter word) to avoid swallowing part of the preceding sentence,
# e.g. "...Institute of Technology\n2022 - 2026" incorrectly matching
# "Technology 2022" as a month+year token.
_MONTH_ALTERNATION = "|".join(sorted(_MONTHS.keys(), key=len, reverse=True))
_DATE_TOKEN = rf"(?:(?:{_MONTH_ALTERNATION})\s+\d{{4}}|\d{{1,2}}/\d{{4}}|\d{{4}})"
_DATE_RANGE_RE = re.compile(
    rf"\b({_DATE_TOKEN})\s*(?:[-\u2013\u2014]|\bto\b)\s*({_DATE_TOKEN}|present|current|ongoing)\b",
    re.IGNORECASE,
)


def _normalize_single_date(token: str) -> str:
    token = token.strip().lower()
    if token in ("present", "current", "ongoing"):
        return "present"
    m = re.match(r"([a-z]{3,9})\s+(\d{4})", token)
    if m:
        mon = _MONTHS.get(m.group(1)[:3] if m.group(1) not in _MONTHS else m.group(1))
        mon = _MONTHS.get(m.group(1), mon)
        if mon:
            return f"{m.group(2)}-{mon}"
        return m.group(2)
    m = re.match(r"(\d{1,2})/(\d{4})", token)
    if m:
        return f"{m.group(2)}-{int(m.group(1)):02d}"
    m = re.match(r"^\d{4}$", token)
    if m:
        return token
    return "unknown"


def normalize_date(date_string: str) -> dict:
    """Parse one date-range mention into {start, end, raw}.
    Robust to garbage: always returns a dict, never raises."""
    if not date_string:
        return {"start": "unknown", "end": "unknown", "raw": date_string or ""}
    m = _DATE_RANGE_RE.search(date_string)
    if not m:
        return {"start": "unknown", "end": "unknown", "raw": date_string.strip()}
    return {
        "start": _normalize_single_date(m.group(1)),
        "end": _normalize_single_date(m.group(2)),
        "raw": date_string.strip(),
    }


def find_all_dates(text: str) -> List[dict]:
    if not text:
        return []
    return [normalize_date(m.group(0)) for m in _DATE_RANGE_RE.finditer(text)]


# ---------------------------------------------------------------------------
# 4. WHITESPACE / NOISE CLEANING
# ---------------------------------------------------------------------------
_BULLET_CHARS_RE = re.compile(r"[•●▪◦∙‣·➤➔→○]")


def clean_text(text: str) -> str:
    """Normalize whitespace, bullet characters, and stray control
    characters without destroying line structure (we still need lines
    to detect section headers)."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _BULLET_CHARS_RE.sub("- ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [ln.strip() for ln in text.split("\n")]
    return "\n".join(lines).strip()
