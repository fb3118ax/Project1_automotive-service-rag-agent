from config.settings import RETRIEVAL_K, embedding_model, TEXT_COLLECTION, DB_PATH, MIN_CHUNK_CHARS, NEAR_DUP_OVERLAP_THRESHOLD
from langchain_chroma import Chroma
import chromadb

client_db = chromadb.PersistentClient(path=DB_PATH)

text_store = Chroma(
    client=client_db,
    collection_name=TEXT_COLLECTION,
    embedding_function=embedding_model
)

# If this fraction of a candidate chunk's words already appear in a
# higher-ranked, already-selected chunk, treat it as a near-duplicate
# (chunker overlap producing two chunks that share most of the same
# paragraph) and skip it rather than let it occupy a top-K slot.
NEAR_DUP_OVERLAP_THRESHOLD = NEAR_DUP_OVERLAP_THRESHOLD


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

    # lower cosine distance = more similar; sort ascending before near-dup filtering
    # so the stronger (lower-distance) chunk of any overlapping pair wins the slot
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