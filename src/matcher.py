"""
Core matching engine: keyword_score() and semantic_score().

Semantic backend: tries sentence-transformers (all-MiniLM-L6-v2) first.
If model weights can't be downloaded (flaky venue wifi, no internet),
it automatically falls back to a TF-IDF + cosine-similarity embedder
from scikit-learn. Both expose the same .encode(list[str]) -> ndarray
interface, so the scoring logic below never needs to know which is active.
This is the "simple but reliable" call: the demo must not die because a
huggingface download timed out mid-hackathon.
"""

import re
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from src.skills_taxonomy import extract_skills_from_text

_BACKEND = None
_BACKEND_NAME = None


class _SBERTBackend:
    def __init__(self):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def prepare(self, corpus_texts):
        # Stateless per text; no batch fitting needed for a real embedding model.
        pass

    def encode(self, texts):
        return self.model.encode(list(texts), show_progress_bar=False)


class _TfidfBackend:
    """Fallback embedder used when sentence-transformers isn't available.

    Uses character n-grams (not word tokens). Word-level TF-IDF is brittle for
    short skill terms: "REST APIs" tokenizes to "apis" (plural) which never
    matches a query for "api" (singular), and "Node.js" vs "NodeJS" vs "node js"
    are all different tokens. Character n-grams are robust to these surface
    variations without needing a hand-maintained synonym list here (that's
    still handled properly upstream by skills_taxonomy.py for keyword matching;
    this is just making the semantic fallback not silently fail on wording).

    IMPORTANT: call prepare(corpus_texts) ONCE per ranking run with the union
    of every text you'll ever encode (JD + all candidates + all chunks/queries)
    before calling encode(). Fitting a fresh vectorizer per-candidate (the old
    behavior) gives each candidate its own tiny, incomparable vector space and
    produces noisy, compressed-toward-zero similarity scores. Fitting once on
    the whole batch gives stable IDF weights and scores that are actually
    comparable across candidates. If prepare() was never called, encode()
    transparently falls back to a fresh fit on just the given texts, so
    existing single-candidate callers (e.g. ad-hoc tests) still work.
    """
    def __init__(self):
        self._vectorizer = None

    def _make_vectorizer(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        return TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), max_features=4096)

    def prepare(self, corpus_texts):
        texts = [t if t and t.strip() else "empty" for t in corpus_texts]
        vec = self._make_vectorizer()
        vec.fit(texts)
        self._vectorizer = vec

    def encode(self, texts):
        texts = [t if t and t.strip() else "empty" for t in texts]
        if self._vectorizer is not None:
            return self._vectorizer.transform(texts).toarray()
        # No batch prepare() call happened — safe one-off fallback.
        vec = self._make_vectorizer()
        return vec.fit_transform(texts).toarray()


def get_backend():
    global _BACKEND, _BACKEND_NAME
    if _BACKEND is not None:
        return _BACKEND
    try:
        _BACKEND = _SBERTBackend()
        _BACKEND_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    except Exception as e:
        _BACKEND = _TfidfBackend()
        _BACKEND_NAME = f"tfidf-fallback ({type(e).__name__})"
    return _BACKEND


def backend_name() -> str:
    get_backend()
    return _BACKEND_NAME


def _is_fallback_backend() -> bool:
    get_backend()
    return _BACKEND_NAME is not None and _BACKEND_NAME.startswith("tfidf-fallback")


def _cosine(a, b) -> float:
    a = np.asarray(a).reshape(1, -1)
    b = np.asarray(b).reshape(1, -1)
    if not a.any() or not b.any():
        return 0.0
    return float(cosine_similarity(a, b)[0][0])


def _chunk_text(text: str, min_len: int = 15) -> list:
    """Split resume text into evidence-sized chunks: lines/sentences long
    enough to be meaningful matches."""
    if not text:
        return []
    raw = re.split(r"[\n\r]|(?<=[.;])\s+", text)
    return [l.strip() for l in raw if len(l.strip()) >= min_len]


# --------------------------- keyword matching -------------------------------

def keyword_score(candidate: dict, jd_analysis: dict) -> dict:
    required = set(jd_analysis.get("required_skills", []))
    preferred = set(jd_analysis.get("preferred_skills", []))

    # Union of P2's explicit skills field + whatever we independently detect
    # in the full text. Keeps scoring robust even if P2's skill extraction
    # is imperfect or a messy resume slips a skill outside the "Skills" section.
    explicit = {s.strip().lower() for s in candidate.get("skills", []) if s.strip()}
    detected_from_text = extract_skills_from_text(
        candidate.get("normalized_text") or candidate.get("raw_text", "")
    )
    detected = explicit | detected_from_text

    matched_required = sorted(required & detected)
    missing_required = sorted(required - detected)
    matched_preferred = sorted(preferred & detected)
    missing_preferred = sorted(preferred - detected)

    required_coverage = (len(matched_required) / len(required)) if required else 1.0
    preferred_coverage = (len(matched_preferred) / len(preferred)) if preferred else 1.0

    # Required skills matter far more than preferred ones.
    score = 100 * (0.75 * required_coverage + 0.25 * preferred_coverage)

    return {
        "score": round(score, 1),
        "matched_required": matched_required,
        "missing_required": missing_required,
        "matched_preferred": matched_preferred,
        "missing_preferred": missing_preferred,
        "formula": "100 * (0.75 * required_coverage + 0.25 * preferred_coverage)",
    }


def _candidate_texts(candidate: dict, jd_analysis: dict) -> list:
    """Every text semantic_score() will need to encode for this one candidate.
    Shared by prepare_batch() (to build the fit corpus) and semantic_score()
    (to know what to transform), so the two never drift out of sync."""
    resume_text = candidate.get("normalized_text") or candidate.get("raw_text", "")
    experience_text = " ".join(candidate.get("experience", []) + candidate.get("projects", []))
    chunks = _chunk_text(experience_text or resume_text)
    skills = candidate.get("skills", [])
    if skills:
        chunks.append("Skills: " + ", ".join(skills))
    return [resume_text or "empty"] + (chunks or ["empty"])


def prepare_batch(jd_analysis: dict, candidates: list) -> None:
    """Fit the TF-IDF fallback (if active) once on the whole batch: JD text,
    every candidate's resume/experience/skills text, and every requirement
    query. No-op for the sentence-transformers backend. Call this once per
    ranking run, before scoring individual candidates — rank_candidates()
    already does this for you.
    """
    backend = get_backend()
    if not hasattr(backend, "prepare"):
        return
    required = jd_analysis.get("required_skills", [])
    preferred = jd_analysis.get("preferred_skills", [])
    corpus = [jd_analysis.get("raw_text", "") or "empty"]
    corpus += [f"experience with {s}" for s in required]
    corpus += [f"experience with {s}" for s in preferred]
    for c in candidates:
        corpus += _candidate_texts(c, jd_analysis)
    backend.prepare(corpus)


# --------------------------- semantic matching -------------------------------

def semantic_score(candidate: dict, jd_analysis: dict) -> dict:
    backend = get_backend()

    jd_text = jd_analysis.get("raw_text", "")
    resume_text = candidate.get("normalized_text") or candidate.get("raw_text", "")
    experience_text = " ".join(candidate.get("experience", []) + candidate.get("projects", []))
    chunks = _chunk_text(experience_text or resume_text)

    # A candidate's declared skills list is real evidence too, not just prose
    # in experience/projects. Without this, a skill that's listed but never
    # mentioned in a sentence (e.g. skills: ["git"], no experience bullet says
    # "git") scores 0.0 semantic similarity even though it's clearly a match.
    skills = candidate.get("skills", [])
    if skills:
        chunks.append("Skills: " + ", ".join(skills))

    chunks = chunks or ["empty"]

    required = jd_analysis.get("required_skills", [])
    preferred = jd_analysis.get("preferred_skills", [])
    req_queries = [f"experience with {s}" for s in required]
    pref_queries = [f"experience with {s}" for s in preferred]

    texts = [jd_text or "empty", resume_text or "empty"] + req_queries + pref_queries + chunks
    embeddings = backend.encode(texts)

    jd_emb, resume_emb = embeddings[0], embeddings[1]
    n_req, n_pref = len(req_queries), len(pref_queries)
    req_embs = embeddings[2:2 + n_req]
    pref_embs = embeddings[2 + n_req:2 + n_req + n_pref]
    chunk_embs = embeddings[2 + n_req + n_pref:]

    overall_sim = max(0.0, _cosine(jd_emb, resume_emb))

    def best_matches(labels, label_embs):
        results = []
        for skill, q_emb in zip(labels, label_embs):
            sims = [_cosine(q_emb, c_emb) for c_emb in chunk_embs]
            best_i = int(np.argmax(sims))
            best_sim = max(0.0, sims[best_i])
            results.append({
                "requirement": skill,
                "score": round(best_sim, 3),
                "snippet": chunks[best_i][:160],
            })
        return results

    req_evidence = best_matches(required, req_embs)
    pref_evidence = best_matches(preferred, pref_embs)

    req_avg = float(np.mean([e["score"] for e in req_evidence])) if req_evidence else overall_sim
    pref_avg = float(np.mean([e["score"] for e in pref_evidence])) if pref_evidence else overall_sim

    if required:
        raw_score = 100 * (0.3 * overall_sim + 0.5 * req_avg + 0.2 * pref_avg)
    else:
        raw_score = 100 * overall_sim
    raw_score = min(100.0, max(0.0, raw_score))

    # Character n-gram TF-IDF cosine similarity is naturally compressed near
    # zero (a genuinely strong match might only score ~0.2-0.3 raw), which is
    # mathematically fine but reads oddly in a demo. Stretch the HEADLINE
    # number only, with a fixed square-root transform - monotonic (never
    # changes rank order or which candidate "wins" a comparison), and not
    # dependent on who else is in the batch (unlike min-max normalization).
    # Per-requirement evidence scores below are left as raw cosine values,
    # since explanations.py's "strong match" threshold is calibrated against
    # the raw scale.
    if _is_fallback_backend():
        display_score = 100 * (raw_score / 100) ** 0.5
    else:
        display_score = raw_score

    return {
        "score": round(display_score, 1),
        "raw_score": round(raw_score, 1),
        "overall_similarity": round(overall_sim, 3),
        "requirement_evidence": req_evidence,
        "preferred_evidence": pref_evidence,
        "backend": backend_name(),
        "formula": (
            "100 * (0.3*overall_sim + 0.5*avg_required_match + 0.2*avg_preferred_match)"
            + (", then sqrt-stretched (fallback backend only, monotonic, batch-independent)"
               if _is_fallback_backend() else "")
        ),
    }
