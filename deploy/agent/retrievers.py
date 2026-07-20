from config.settings import RETRIEVAL_K, embedding_model, TEXT_COLLECTION, DB_PATH, MIN_CHUNK_CHARS, NEAR_DUP_OVERLAP_THRESHOLD
from langchain_chroma import Chroma
import chromadb
import logging
import math

# Optional cross-encoder reranker (better ranking of query/chunk pairs)
try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # FIX: needs the "cross-encoder/" HF namespace prefix
    _cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL)
except Exception:
    _cross_encoder = None
    logging.getLogger(__name__).info("CrossEncoder not available; falling back to raw vector similarity.")

client_db = chromadb.PersistentClient(path=DB_PATH)

text_store = Chroma(
    client=client_db,
    collection_name=TEXT_COLLECTION,
    embedding_function=embedding_model
)


def _is_near_duplicate(content, selected_contents):
    words = set(content.lower().split())
    if not words:
        return False
    for selected in selected_contents:
        selected_words = set(selected.lower().split())
        if not selected_words:
            continue
        overlap = len(words & selected_words) / len(words)
        if overlap >= NEAR_DUP_OVERLAP_THRESHOLD:
            return True
    return False


def text_retriever(state):
    seen_contents = set()
    candidates = []
    all_queries = [state["query"]] + state["query_variations"]

    for query in all_queries:
        
        results = text_store.similarity_search_with_score(query, k=RETRIEVAL_K)
        for doc, score in results:
            content = doc.page_content
            if len(content.strip()) < MIN_CHUNK_CHARS:
                continue
            dedup_key = content.strip().lower()
            if dedup_key not in seen_contents:
                seen_contents.add(dedup_key)
                candidates.append({"content": content, "metadata": doc.metadata, "score": score})

    # Optionally rerank candidates with a cross-encoder (query, chunk) scorer.
    # If available, score each pair and sort by that score (higher = better).
    # IMPORTANT: confidence_score.py consumes c["score"] for rank-weighted
    # averaging. If we reorder by rerank_score but leave "score" as the stale
    # cosine distance, confidence would be computed against a ranking that no
    # longer matches "score" order. So when reranking succeeds, we overwrite
    # "score" with a distance-shaped value derived from rerank_score (lower =
    # better, consistent with the raw cosine-distance convention downstream).
    if _cross_encoder is not None:
        try:
            qe = state.get("query", "")
            pairs = [(qe, c["content"]) for c in candidates]
            rerank_scores = _cross_encoder.predict(pairs)
            for c, s in zip(candidates, rerank_scores):
                c["rerank_score"] = float(s)

            # higher rerank_score = more relevant -> sort descending
            candidates.sort(key=lambda c: c.get("rerank_score", -float("inf")), reverse=True)
            # Cross-encoder logits are unbounded (seen range roughly -10..+11
            # in practice), unlike cosine distance which is naturally bounded
            # ~0-2. Feeding raw/negated logits into confidence_score.py's
            # distance-based normalization saturates confidence to ~1.0
            # regardless of actual match quality. Squash through a sigmoid to
            # get a bounded (0,1) pseudo-probability first - this is the
            # standard interpretation of a cross-encoder logit - then convert
            # to a distance-like value (lower = better) so it's consistent
            # with the "lower score = better" convention confidence_score.py
            # already expects from cosine distance.
            for c in candidates:
                prob = 1.0 / (1.0 + math.exp(-c["rerank_score"]))
                c["score"] = 1.0 - prob
        except Exception:
            logging.getLogger(__name__).exception("Cross-encoder rerank failed; falling back to vector score ordering")
            candidates.sort(key=lambda c: c["score"])
    else:
        # lower cosine distance = more similar; keep original behavior
        candidates.sort(key=lambda c: c["score"])
    chunks = []
    selected_contents = []
    for c in candidates:
        if _is_near_duplicate(c["content"], selected_contents):
            continue
        chunks.append(c)
        selected_contents.append(c["content"])
        if len(chunks) == RETRIEVAL_K:
            break

    return {"retrieved_chunks": chunks}