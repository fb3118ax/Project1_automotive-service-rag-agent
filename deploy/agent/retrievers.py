import os
import json
import hashlib
from config.settings import (
    RETRIEVAL_K, embedding_model, TEXT_COLLECTION, IMAGE_COLLECTION, DB_PATH,
    IMAGE_REQUEST_KEYWORDS, IMAGE_CANDIDATE_K, IMAGE_MAX_RESULTS,
    client, LLM_MODEL,
)
from langchain_chroma import Chroma
import chromadb

client_db = chromadb.PersistentClient(path=DB_PATH)

text_store = Chroma(
    client=client_db,
    collection_name=TEXT_COLLECTION,
    embedding_function=embedding_model
)

image_store = Chroma(
    client=client_db,
    collection_name=IMAGE_COLLECTION,
    embedding_function=embedding_model
)

image_collection_raw = client_db.get_collection(IMAGE_COLLECTION)

# ── Azure Blob Storage base URL ───────────────────────────────────────────────
AZURE_STORAGE_BASE_URL = os.getenv(
    "AZURE_STORAGE_BASE_URL",
    "https://mechaistorage.blob.core.windows.net/local-images"
)


def build_blob_url(local_path: str) -> str:
    """
    Convert local image path to Azure Blob Storage URL.
    e.g. images/page_101_image_0.png
      -> https://mechaistorage.blob.core.windows.net/local-images/page_101_image_0.png
    """
    filename = os.path.basename(local_path)
    return f"{AZURE_STORAGE_BASE_URL}/{filename}"


def text_retriever(state):
    # Unchanged from before.
    seen_contents = set()
    chunks = []

    all_queries = [state["query"]] + state["query_variations"]

    for query in all_queries:
        results = text_store.similarity_search_with_score(query, k=RETRIEVAL_K)
        for doc, score in results:
            if doc.page_content not in seen_contents:
                seen_contents.add(doc.page_content)
                chunks.append({
                    "content":  doc.page_content,
                    "metadata": doc.metadata,
                    "score":    score
                })

    return {"retrieved_chunks": chunks}


def _gather_image_candidates(state):
    """
    Build the candidate pool for image_retriever, BEFORE relevance filtering.
    Two independent sources, unioned — neither alone was reliable:

      1) page-matched: any image whose page_number matches a page already
         retrieved by text_retriever. Catches the case where the right
         image exists but its own GPT-4o caption doesn't embed close to
         the query wording.
      2) raw-query: direct semantic search against image captions (the
         original approach). Catches the case where the right image lives
         on a page the text retriever didn't surface at all.

    Each candidate keeps its caption — the LLM reranker below judges
    relevance from caption text, not image bytes, so the caption has to
    travel with the candidate.
    """
    candidates = {}  # image_path -> {"path", "caption", "page_number"}

    # 1) page-matched candidates
    retrieved_pages = sorted({
        chunk["metadata"].get("page_number")
        for chunk in state.get("retrieved_chunks", [])
        if chunk["metadata"].get("page_number") is not None
    })
    if retrieved_pages:
        try:
            page_matches = image_collection_raw.get(
                where={"page_number": {"$in": retrieved_pages}},
                include=["documents", "metadatas"]
            )
            for doc_text, meta in zip(page_matches.get("documents", []),
                                       page_matches.get("metadatas", [])):
                path = meta.get("image_path")
                if path:
                    candidates[path] = {
                        "path": path,
                        "caption": doc_text,
                        "page_number": meta.get("page_number"),
                    }
        except Exception as e:
            # A failed metadata lookup should never break the answer —
            # fall through to raw-query candidates only.
            print(f"Page-matched image lookup failed: {e}")

    # 2) raw-query candidates (same mechanism as before, k now configurable)
    all_queries = [state["query"]] + state["query_variations"]
    for query in all_queries:
        results = image_store.similarity_search_with_score(query, k=IMAGE_CANDIDATE_K)
        for doc, score in results:
            path = doc.metadata.get("image_path", "")
            if path and path not in candidates:
                candidates[path] = {
                    "path": path,
                    "caption": doc.page_content,
                    "page_number": doc.metadata.get("page_number"),
                }

    return list(candidates.values())


def _rerank_images(query, candidates):
    """
    One batched LLM call: given the query and every candidate's caption,
    keep only the captions that genuinely answer/illustrate THIS specific
    query, ordered most-to-least relevant.

    Why an LLM call instead of a similarity-score threshold: the bug this
    is fixing is page-level false positives — a single page can carry
    several images for different subsections (the page-271 parking example
    from earlier), so "same page as the text answer" isn't sufficient on
    its own. Captions are short, so one batched call stays cheap regardless
    of candidate count.

    Fails safe: any parsing problem returns the candidates as-is (capped),
    rather than showing nothing or crashing the whole request over an image
    formatting issue.
    """
    if not candidates:
        return []
    if len(candidates) == 1:
        return candidates  # nothing to rank against

    numbered = "\n".join(
        f"{i}: {c['caption']}" for i, c in enumerate(candidates)
    )
    prompt = f"""User question: "{query}"

Below are candidate image captions from a BMW manual, numbered.
Return ONLY a JSON array of the index numbers of captions that show
something a person would actually expect to see when answering this
specific question. Exclude images that are merely on the same page but
illustrate a different topic. Order the array from most to least relevant.
Return [] if none are relevant. No other text, no markdown fences.

{numbered}"""

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            timeout=30,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        kept_indices = json.loads(raw)
        kept = [
            candidates[i] for i in kept_indices
            if isinstance(i, int) and 0 <= i < len(candidates)
        ]
        return kept[:IMAGE_MAX_RESULTS]
    except Exception as e:
        print(f"Image rerank failed, falling back to unranked candidates: {e}")
        return candidates[:IMAGE_MAX_RESULTS]


def image_retriever(state):
    """
    Runs AFTER text_retriever now (graph.py changed from parallel to
    sequential) so it can read state["retrieved_chunks"] for page-matching.

    Gating moved here from conversation.py: images are only ever attempted
    if the query explicitly asks for one (same keyword list as before, now
    centralized in settings.py as IMAGE_REQUEST_KEYWORDS). conversation.py
    no longer carries any image-specific logic — it just displays whatever
    image_paths comes back, which by the time it gets there has already
    been through the explicit-request gate, the candidate union, and the
    relevance rerank.
    """
    query_lower = state["query"].lower()
    explicit_image_request = any(word in query_lower for word in IMAGE_REQUEST_KEYWORDS)
    if not explicit_image_request:
        return {"image_paths": []}

    candidates = _gather_image_candidates(state)
    kept = _rerank_images(state["query"], candidates)

    image_urls = [build_blob_url(c["path"]) for c in kept]
    return {"image_paths": image_urls}