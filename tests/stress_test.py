"""
stress_test.py
===============
Edge-case testing beyond the 3 happy-path synthetic resumes. Generates
resumes/JDs designed to break the parser in ways the real 18 resumes
plausibly could, and reports pass/fail for each scenario instead of just
printing raw output.

Run from the tests/ folder:  python3 stress_test.py
"""

import os
import sys
import io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from pypdf import PdfWriter

import parser
import normalizer

EDGE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "edge_cases")
os.makedirs(EDGE_DIR, exist_ok=True)

results = []  # (name, passed: bool, detail: str)


def check(name, condition, detail=""):
    results.append((name, bool(condition), detail))


def write_pdf(path, lines):
    c = canvas.Canvas(path, pagesize=letter)
    width, height = letter
    y = height - 50
    for line in lines:
        c.drawString(50, y, line)
        y -= 16
        if y < 50:
            c.showPage()
            y = height - 50
    c.save()


# ---------------------------------------------------------------------------
# Case 1: Blank / genuinely empty PDF (simulates a scanned resume with no
# extractable text layer)
# ---------------------------------------------------------------------------
blank_path = os.path.join(EDGE_DIR, "blank.pdf")
writer = PdfWriter()
writer.add_blank_page(width=612, height=792)
with open(blank_path, "wb") as f:
    writer.write(f)

c = parser.parse_resume(blank_path)
check(
    "Blank/scanned PDF -> parse_ok False, no crash",
    c["parse_ok"] is False and c["parse_error"],
    f"parse_ok={c['parse_ok']}, parse_error={c['parse_error']!r}",
)

# ---------------------------------------------------------------------------
# Case 2: Corrupt file (not a real PDF at all, just garbage bytes with a
# .pdf extension -- simulates a bad upload/export)
# ---------------------------------------------------------------------------
corrupt_path = os.path.join(EDGE_DIR, "corrupt.pdf")
with open(corrupt_path, "wb") as f:
    f.write(b"this is not a real pdf file, just bytes\x00\x01\x02")

c = parser.parse_resume(corrupt_path)
check(
    "Corrupt/non-PDF file -> parse_ok False, no crash",
    c["parse_ok"] is False,
    f"parse_ok={c['parse_ok']}, parse_error={c['parse_error']!r}",
)

# ---------------------------------------------------------------------------
# Case 3: Resume with NO skills section at all -- skills only appear
# scattered in free-text experience bullets. Should still pick them up via
# the full-text scan fallback.
# ---------------------------------------------------------------------------
no_skills_section = [
    "Karan Mehta",
    "karan.mehta@email.com",
    "",
    "EXPERIENCE",
    "Software Engineering Intern, DataWorks Inc.",
    "May 2023 - Aug 2023",
    "- Built backend services in Python using Flask and PostgreSQL",
    "- Deployed services to AWS using Docker containers",
    "",
    "EDUCATION",
    "B.Tech Information Technology, VIT",
    "2021 - 2025",
]
p = os.path.join(EDGE_DIR, "no_skills_section.pdf")
write_pdf(p, no_skills_section)
c = parser.parse_resume(p)
expected = {"Python", "Flask", "PostgreSQL", "AWS", "Docker"}
found = set(c["skills"])
check(
    "No dedicated skills section -> skills still found via full-text scan",
    expected.issubset(found),
    f"expected subset of {expected}, got {found}",
)

# ---------------------------------------------------------------------------
# Case 4: Unrecognized/unusual section headers not in SECTION_HEADER_MAP
# (e.g. "What I've Built" instead of "Projects", "Where I Studied" instead
# of "Education") -- these should NOT crash, but will legitimately fall
# outside the canonical experience/education/projects/skills buckets.
# This test documents that behavior rather than asserting it's "wrong".
# ---------------------------------------------------------------------------
unusual_headers = [
    "Sneha Rao",
    "sneha.rao@email.com",
    "",
    "MY TOOLKIT",
    "React, Node.js, MongoDB, Git",
    "",
    "WHAT I'VE BUILT",
    "Portfolio Site - React, deployed on Vercel",
    "",
    "WHERE I STUDIED",
    "B.E Computer Science, RVCE",
    "2022 - 2026",
]
p = os.path.join(EDGE_DIR, "unusual_headers.pdf")
write_pdf(p, unusual_headers)
c = parser.parse_resume(p)
check(
    "Unusual section headers -> no crash, parse_ok True",
    c["parse_ok"] is True,
    f"parse_ok={c['parse_ok']}",
)
check(
    "Unusual headers -> skills still found via full-text fallback even though "
    "'MY TOOLKIT' isn't a recognized skills header",
    {"React", "Node.js", "MongoDB", "Git"}.issubset(set(c["skills"])),
    f"skills found: {c['skills']}",
)

# ---------------------------------------------------------------------------
# Case 5: Heavy typos / spacing noise in skill names, beyond what
# candidate_02 already covers -- tests difflib fuzzy-match tolerance and
# where it should legitimately fail (typos too far from any known term).
# ---------------------------------------------------------------------------
typo_tests = [
    ("reactjs", "React"),
    ("nodejs", "Node.js"),
    ("mongo db", "MongoDB"),
    ("expresss", "Express"),      # 1 extra letter, should still fuzzy-match
    ("pyhton", "Python"),          # transposition typo
    ("javascrpt", "JavaScript"),   # dropped letter
    ("xyzzy123", None),            # should NOT match anything
]
for raw, expected_canon in typo_tests:
    got = normalizer.normalize_skill(raw)
    check(
        f"normalize_skill({raw!r}) -> {expected_canon!r}",
        got == expected_canon,
        f"got {got!r}",
    )

# ---------------------------------------------------------------------------
# Case 6: JD phrased without the exact marker words the extractor looks for
# (no "Requirements"/"Preferred"/"Responsibilities" headings at all -- just
# prose). Should fall back to scanning the whole doc for skills rather than
# returning empty lists.
# ---------------------------------------------------------------------------
prose_jd = [
    "Backend Developer Intern",
    "Orbit Systems",
    "",
    "We're building a small internal tool and need someone comfortable with",
    "Python, Django, and PostgreSQL to help out for a few months. Nice to",
    "have if you also know Docker or have touched AWS before, but that's",
    "not essential. You'll mostly be writing REST APIs and fixing bugs.",
]
p = os.path.join(EDGE_DIR, "prose_jd.pdf")
write_pdf(p, prose_jd)
jd = parser.parse_jd(p)
all_found_skills = set(jd["required_skills"]) | set(jd["preferred_skills"])
check(
    "JD with no explicit Requirements/Preferred headers -> "
    "still extracts skills via full-text fallback",
    {"Python", "Django", "PostgreSQL"}.issubset(all_found_skills),
    f"required={jd['required_skills']}, preferred={jd['preferred_skills']}",
)

# ---------------------------------------------------------------------------
# Case 7: Batch run mixing good + broken files -- confirms one bad file
# doesn't take down the whole batch (the core promise of the module).
# ---------------------------------------------------------------------------
mixed_paths = [
    os.path.join(EDGE_DIR, "blank.pdf"),
    os.path.join(EDGE_DIR, "corrupt.pdf"),
    os.path.join(EDGE_DIR, "no_skills_section.pdf"),
    os.path.join(EDGE_DIR, "unusual_headers.pdf"),
]
batch = parser.batch_process_resumes(mixed_paths)
ok_count = sum(1 for c in batch if c["parse_ok"])
check(
    "Mixed good+broken batch -> no exception, correct ok/fail split",
    len(batch) == 4 and ok_count == 2,
    f"got {len(batch)} results, {ok_count} parsed ok (expected 2)",
)

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
print("=" * 70)
passed = 0
for name, ok, detail in results:
    status = "PASS" if ok else "FAIL"
    if ok:
        passed += 1
    print(f"[{status}] {name}")
    if not ok:
        print(f"        -> {detail}")
print("=" * 70)
print(f"{passed}/{len(results)} checks passed")
if passed != len(results):
    sys.exit(1)
