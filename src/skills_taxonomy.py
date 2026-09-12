"""
Canonical skill taxonomy with alias normalization.

Used by BOTH the JD analyzer and the resume keyword matcher so that
"ReactJS", "React.js", "react js" all resolve to the same canonical
skill "react". This is what makes keyword matching more than dumb
substring search.

Extend SKILL_ALIASES during the hackathon if a sample JD uses a term
we don't cover yet - that's a 30-second edit, not a redesign.
"""

import re

# canonical_skill -> list of surface-form variants (matched case-insensitively
# with word boundaries, see _COMPILED below).
SKILL_ALIASES = {
    "python": ["python", "python3"],
    "java": ["java"],
    "javascript": ["javascript", "es6", "ecmascript"],
    "typescript": ["typescript"],
    "c++": ["c++", "cpp"],
    "c#": ["c#", "csharp"],
    "go": ["golang"],  # bare "go" excluded on purpose - too common an English word
    "react": ["react", "reactjs", "react js"],
    "angular": ["angular", "angularjs"],
    "vue": ["vue", "vuejs", "vue js"],
    "node.js": ["node.js", "nodejs", "node js"],
    "express": ["express", "expressjs", "express.js"],
    "django": ["django"],
    "flask": ["flask"],
    "fastapi": ["fastapi", "fast api"],
    "spring": ["spring boot", "springboot", "spring"],
    "html": ["html", "html5"],
    "css": ["css", "css3"],
    "sql": ["sql"],
    "mysql": ["mysql"],
    "postgresql": ["postgresql", "postgres"],
    "mongodb": ["mongodb", "mongo db", "mongo"],
    "redis": ["redis"],
    "aws": ["aws", "amazon web services"],
    "azure": ["azure", "microsoft azure"],
    "gcp": ["gcp", "google cloud platform", "google cloud"],
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
    "git": ["git", "github", "gitlab"],
    "ci/cd": ["ci/cd", "ci cd", "continuous integration", "continuous deployment"],
    "rest api": ["rest api", "restful api", "rest apis", "restful"],
    "graphql": ["graphql"],
    "machine learning": ["machine learning"],
    "deep learning": ["deep learning"],
    "nlp": ["nlp", "natural language processing"],
    "computer vision": ["computer vision"],
    "tensorflow": ["tensorflow"],
    "pytorch": ["pytorch"],
    "scikit-learn": ["scikit-learn", "sklearn", "scikit learn"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "data structures": ["data structures", "dsa"],
    "algorithms": ["algorithms"],
    "linux": ["linux", "unix"],
    "bash": ["bash", "shell scripting"],
    "agile": ["agile", "scrum"],
    "microservices": ["microservices", "micro services"],
    "kafka": ["kafka", "apache kafka"],
    "spark": ["spark", "apache spark"],
    "hadoop": ["hadoop"],
    "streamlit": ["streamlit"],
    "flutter": ["flutter"],
    "react native": ["react native"],
    "android": ["android"],
    "ios": ["ios", "swift"],
    "figma": ["figma"],
    "tableau": ["tableau"],
    "power bi": ["power bi", "powerbi"],
    "excel": ["excel", "ms excel"],
    "jira": ["jira"],
    "terraform": ["terraform"],
    "jenkins": ["jenkins"],
    "selenium": ["selenium"],
    "junit": ["junit"],
    "pytest": ["pytest"],
    "firebase": ["firebase"],
    "next.js": ["next.js", "nextjs", "next js"],
    "tailwind": ["tailwind", "tailwindcss", "tailwind css"],
    "redux": ["redux"],
    "webpack": ["webpack"],
}

# Pre-compile one regex per canonical skill: matches any alias as a whole
# word/phrase (no partial-word false positives, e.g. "react" won't match "reactor").
_COMPILED = {
    canonical: re.compile(
        r"(?<![a-z0-9])(" + "|".join(re.escape(a.strip()) for a in aliases) + r")(?![a-z0-9])",
        re.IGNORECASE,
    )
    for canonical, aliases in SKILL_ALIASES.items()
}


def normalize_text(text: str) -> str:
    """Lowercase + collapse whitespace. Keeps punctuation like '.', '#', '+'
    since it's meaningful for skills such as 'c++', 'node.js', 'c#'."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.lower()).strip()


def extract_skills_from_text(text: str) -> set:
    """Return the set of canonical skills detected anywhere in free text."""
    norm = normalize_text(text)
    if not norm:
        return set()
    return {canonical for canonical, pattern in _COMPILED.items() if pattern.search(norm)}
