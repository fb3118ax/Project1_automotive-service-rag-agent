import os
import json
from config.settings import (
    RETRIEVAL_K, embedding_model, TEXT_COLLECTION, IMAGE_COLLECTION, DB_PATH,
    IMAGE_REQUEST_KEYWORDS, IMAGE_CANDIDATE_K, IMAGE_MAX_RESULTS,
    client, LLM_MODEL,
)
from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage
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


AZURE_STORAGE_BASE_URL = os.getenv(
    "AZURE_STORAGE_BASE_URL",
    "https://mechaistorage.blob.core.windows.net/local-images"
)


def build_blob_url(local_path: str) -> str:
    filename = os.path.basename(local_path)
    return f"{AZURE_STORAGE_BASE_URL}/{filename}"


def _is_context_free_image_request(query: str) -> bool:
    """
    Returns True if the query contains only image-request keywords with no
    actual topic — e.g. "show me the image", "picture", "show me a diagram".
    These queries need prior conversation context to rerank against, otherwise
    the reranker has nothing meaningful to judge relevance with.
    """
    allowed = {"show", "me", "the", "image", "images", "picture", "pictures",
               "diagram", "diagrams", "a", "an", "photo", "photos", "visual",
               "visuals", "please"}
    words = set(query.lower().split())
    return words.issubset(allowed)


def text_retriever(state):
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
    candidates = {}

    
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
            print(f"Page-matched image lookup failed: {e}")

    
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
    if not candidates:
        return []
    if len(candidates) == 1:
        return candidates

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
    query_lower = state["query"].lower()
    explicit_image_request = any(word in query_lower for word in IMAGE_REQUEST_KEYWORDS)
    if not explicit_image_request:
        return {"image_paths": []}

    rerank_query = state["query"]
    if _is_context_free_image_request(state["query"]):
        current_topic = state.get("current_topic", "").strip()
        if current_topic:
            rerank_query = current_topic
        else:
            return {"image_paths": []}

    corrected_state = {**state, "query": rerank_query, "query_variations": []}
    corrected_chunks = text_retriever(corrected_state)
    state_for_candidates = {**state,
                            "query": rerank_query,
                            "query_variations": [],
                            "retrieved_chunks": corrected_chunks["retrieved_chunks"]}
    candidates = _gather_image_candidates(state_for_candidates)
    kept = _rerank_images(rerank_query, candidates)

    image_urls = [build_blob_url(c["path"]) for c in kept]
    return {"image_paths": image_urls}
