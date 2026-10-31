import math
from datetime import datetime, timezone

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _doc_text(c):
    # Title is repeated so it carries more weight than the description
    return " ".join([
        c["title"], c["title"], c["title"],
        " ".join(c.get("tags", [])), " ".join(c.get("tags", [])),
        c.get("category", ""),
        c.get("description", ""),
    ])


def rank_courses(docs, query, limit=20):
    """Return up to `limit` (course, score) pairs ordered by relevance."""
    if not docs:
        return []

    query = query.strip()
    if not query:
        ordered = sorted(docs, key=lambda c: c.get("views", 0), reverse=True)
        return [(c, 0.0) for c in ordered[:limit]]

    texts = [_doc_text(c) for c in docs]

    # Word n-grams capture meaning ("machine learning" as a phrase)
    word_vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
    word_matrix = word_vec.fit_transform(texts)
    word_sim = cosine_similarity(word_vec.transform([query]), word_matrix)[0]

    # Character n-grams tolerate typos and partial words
    char_vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
    char_matrix = char_vec.fit_transform(texts)
    char_sim = cosine_similarity(char_vec.transform([query]), char_matrix)[0]

    relevance = 0.6 * word_sim + 0.4 * char_sim
    now = datetime.now(timezone.utc)

    scored = []
    for i, c in enumerate(docs):
        if relevance[i] <= 0.02:          # skip courses that don't match at all
            continue
        uploaded = c["uploaded_at"]
        if uploaded.tzinfo is None:
            uploaded = uploaded.replace(tzinfo=timezone.utc)
        age_days = max((now - uploaded).days, 0)

        popularity = math.log10(c.get("views", 0) + 1) / 6   # roughly 0 to 1
        freshness = 1 / (1 + age_days / 365)                 # newer scores higher

        score = 0.8 * relevance[i] + 0.1 * popularity + 0.1 * freshness
        scored.append((c, score))

    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:limit]


def autocomplete(docs, prefix, limit=8):
    """Suggest titles and tags that start with the prefix or any word in them."""
    p = prefix.strip().lower()
    if not p:
        return []
    suggestions = {}
    for c in sorted(docs, key=lambda c: c.get("views", 0), reverse=True):
        for term in [c["title"], *c.get("tags", [])]:
            t = term.lower()
            if t.startswith(p) or any(w.startswith(p) for w in t.split()):
                suggestions.setdefault(t, term)
    return list(suggestions.values())[:limit]
