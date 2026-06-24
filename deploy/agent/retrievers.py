from config.settings import RETRIEVAL_K, embedding_model, TEXT_COLLECTION, IMAGE_COLLECTION, DB_PATH
from langchain_chroma import Chroma
import chromadb
import os

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


def image_retriever(state):
    """
    Query image_chunks collection and return Azure Blob URLs
    for images relevant to the query.
    """
    seen_paths = set()
    image_urls = []

    all_queries = [state["query"]] + state["query_variations"]

    for query in all_queries:
        results = image_store.similarity_search_with_score(query, k=2)  # k=2 to limit token usage
        for doc, score in results:
            local_path = doc.metadata.get("image_path", "")
            if not local_path or local_path in seen_paths:
                continue
            seen_paths.add(local_path)
            blob_url = build_blob_url(local_path)
            image_urls.append(blob_url)

    return {"image_paths": image_urls}