# P2 Deliverable — Resume/JD Processing + Messy-Resume Bonus

## Files
```
src/schemas.py      Shared data contract (Candidate, JobDescription dicts)
src/normalizer.py   Skill aliasing, section-header aliasing, date parsing, text cleaning
src/parser.py       PDF extraction, resume/JD structuring, batch processing
tests/make_test_pdfs.py  Generates 3 synthetic test resumes + a JD (for local testing only)
```

## Setup
```
pip install -r requirements.txt
```
(`difflib` used for typo-tolerant skill matching is Python stdlib — no extra package needed.)

## How to run / test it
```
cd src
python3 -c "
import parser
cands = parser.process_all_resumes('../data/resumes')
for c in cands:
    parser.debug_print_candidate(c)
jd = parser.parse_jd('../data/jd/Sample_JD.pdf')
print(jd['required_skills'], jd['preferred_skills'])
"
```
Or generate the bundled synthetic test set first: `python3 tests/make_test_pdfs.py`

## Example output (from the synthetic test set)
```
candidate_01  (Priya Sharma)
  Parsed OK: YES
  Skills: JavaScript, Node.js, Express, MongoDB, React, Git, REST API, Redux
  Experience lines: 4
  Projects lines: 2
  Education lines: 2
  Dates found: [{'start': '2024-01', 'end': 'present', 'raw': 'Jan 2024 - Present'}, ...]

candidate_02  (RAHUL VERMA)      <- deliberately messy input, still parses cleanly
  Parsed OK: YES
  Skills: React, MongoDB, Node.js, JavaScript                <- "node js", "mongo db", "react js" all normalized
  Experience lines: 4
  ...
```

## Exact interface for P1

```python
from parser import (
    extract_pdf_text,        # (path: str) -> str
    parse_resume,             # (path: str) -> Candidate   (alias: extract_resume)
    parse_jd,                 # (path: str) -> JobDescription  (alias: extract_jd)
    batch_process_resumes,    # (paths: list[str]) -> list[Candidate]
    process_all_resumes,      # (resume_directory: str) -> list[Candidate]
    debug_print_candidate,    # (Candidate) -> None, for debugging
)
from normalizer import normalize_skill, normalize_date   # if P1 needs these directly
```

**`Candidate` dict** (see `schemas.py` for the full typed definition):
```python
{
    "id": "candidate_01",
    "name": "Priya Sharma",
    "source_file": "candidate_01.pdf",
    "raw_text": "...",
    "normalized_text": "...",
    "sections": {"experience": "...", "skills": "...", "education": "...", "projects": "..."},
    "skills": ["React", "Node.js", "Express", "MongoDB", ...],   # canonicalized, deduped
    "experience": ["line 1", "line 2", ...],
    "education": [...],
    "projects": [...],
    "dates": [{"start": "2024-01", "end": "present", "raw": "Jan 2024 - Present"}, ...],
    "parse_ok": True,
    "parse_error": None,
}
```

**`JobDescription` dict**:
```python
{
    "source_file": "Sample_JD.pdf",
    "raw_text": "...",
    "normalized_text": "...",
    "role_title": "Junior Full Stack Developer Intern",
    "required_skills": ["REST API", "Node.js", "Express", "MongoDB", "React"],
    "preferred_skills": ["TypeScript", "Docker", "AWS"],
    "experience_requirement": "0-1 years of experience",
    "education_requirement": "Bachelor's degree in Computer Science or related field preferred",
    "responsibilities": ["Build and maintain REST APIs...", ...],
    "sections": {...},
}
```

**Important for P1's matching logic:** `candidate["skills"]` and `jd["required_skills"]`/`jd["preferred_skills"]`
are already canonicalized through the same `normalize_skill` alias map — so a straightforward
set-intersection (`set(candidate["skills"]) & set(jd["required_skills"])`) already gets you clean,
typo-tolerant, alias-tolerant keyword matching. You don't need to re-normalize anything on your end.

If a candidate has `parse_ok == False`, skip it from scoring or score it 0 — don't assume any of the
other fields are populated (they'll be empty).

## What's handled for the messy-resume bonus
- Whitespace/bullet-character noise cleanup (multiple spaces, stray bullets, inconsistent line breaks)
- Section header aliasing ("Professional Experience" / "Employment History" / "Internships" → `experience`, etc.)
- Skill aliasing + lightweight typo tolerance ("ReactJS", "react js", "mongo db" → canonical names)
- Date format normalization ("Jan 2024", "01/2024", "2024" → `{"start": "2024-01", ...}`)
- Per-resume error isolation — one corrupt/scanned PDF returns `parse_ok: False` instead of crashing the batch

## Not built here (by design — see spec)
No UI, no semantic matching/embeddings, no ranking/scoring logic, no LLM calls. This module only
produces clean structured data for P1 to score against.

---

## Message to send P1

> Parsing + normalization is done and tested end-to-end (ran it against synthetic resumes with
> deliberately messy formatting — typos, inconsistent spacing/headers/dates — and it parses clean).
> Import from `src/parser.py`: call `process_all_resumes(resume_directory)` to get a list of
> `Candidate` dicts, and `parse_jd(jd_path)` to get the `JobDescription` dict. Both are already
> defined in `src/schemas.py` if you want the full field list.
>
> Key thing for your scoring logic: `candidate["skills"]`, `jd["required_skills"]`, and
> `jd["preferred_skills"]` are all pre-canonicalized through the same alias map, so you can do a
> straight set intersection for keyword matching without re-normalizing anything. `candidate["dates"]`,
> `candidate["experience"]`/`["projects"]`/`["education"]` are also there if you want extra signal
> beyond just skills.
>
> If a candidate failed to parse (bad/scanned PDF), `parse_ok` will be `False` — please skip or
> zero-score those rather than assuming the other fields are populated.
