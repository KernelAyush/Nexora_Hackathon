"""
Bonus feature: flags potentially biased / overly narrow JD wording.
Pure rule-based heuristics - fast, transparent, and safe to wrap in a
try/except from app.py so it can never take down the core ranking pipeline.
"""

import re

GENDERED_TERMS = {
    "rockstar": "coded, informal language that can discourage some applicants",
    "ninja": "coded, informal language that can discourage some applicants",
    "guru": "coded, informal language that can discourage some applicants",
    "aggressive": "masculine-coded wording linked to lower application rates from women",
    "dominant": "masculine-coded wording",
    "superhero": "coded, informal language",
}

AGE_CODED_TERMS = {
    "digital native": "can be read as an age/generation proxy",
    "recent graduate": "may exclude experienced career-changers",
    "young and energetic": "age-coded phrasing",
}

_YEARS_PATTERN = re.compile(r"\b(\d{1,2})\+?\s*years?\b")


def analyze_jd_bias(jd_text: str, required_skills=None) -> dict:
    text = jd_text.lower()
    flags = []

    for term, why in {**GENDERED_TERMS, **AGE_CODED_TERMS}.items():
        if term in text:
            flags.append({"type": "wording", "term": term, "explanation": why})

    for m in _YEARS_PATTERN.finditer(text):
        years = int(m.group(1))
        if years >= 8:
            flags.append({
                "type": "experience_requirement",
                "term": m.group(0),
                "explanation": f"a {years}+ year requirement may be unnecessarily "
                               f"restrictive unless this is genuinely a senior/lead role",
            })

    if required_skills and len(required_skills) > 10:
        flags.append({
            "type": "requirement_volume",
            "term": f"{len(required_skills)} required skills",
            "explanation": "an unusually long required-skills list can exclude "
                            "otherwise strong candidates missing 1-2 items; consider "
                            "moving some items to 'preferred'",
        })

    if not flags:
        severity = "none"
    elif len(flags) <= 2:
        severity = "low"
    elif len(flags) <= 4:
        severity = "medium"
    else:
        severity = "high"

    return {
        "flags": flags,
        "severity": severity,
        "explanation": (
            f"Found {len(flags)} potential bias/narrowness flag(s)." if flags
            else "No obvious bias indicators detected by our heuristics."
        ),
        "suggestions": [
            "Reframe subjective/coded adjectives (e.g. 'rockstar') as concrete, "
            "measurable requirements.",
            "Split 'required' into true must-haves vs. 'preferred' for anything "
            "learnable on the job.",
            "Double-check high year-of-experience thresholds against the actual "
            "seniority of the role.",
        ] if flags else [],
    }
