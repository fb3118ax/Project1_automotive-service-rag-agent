from config.settings import RETRIEVAL_K, embedding_model, TEXT_COLLECTION, DB_PATH, MIN_CHUNK_CHARS
from langchain_chroma import Chroma
import chromadb

client_db = chromadb.PersistentClient(path=DB_PATH)

text_store = Chroma(
    client=client_db,
    collection_name=TEXT_COLLECTION,
    embedding_function=embedding_model
)


def text_retriever(state):
    seen_contents = set()
    chunks = []
    all_queries = [state["query"]] + state["query_variations"]

    for query in all_queries:
        results = text_store.similarity_search_with_score(query, k=RETRIEVAL_K)
        for doc, score in results:
            content = doc.page_content
            if len(content.strip()) < MIN_CHUNK_CHARS:
                continue
            # normalized (lowercased) as the dedup key only — the LLM still sees
            # the original casing in `content`, this just stops "Notes" vs "notes"
            # style case variants from being double-counted as distinct chunks
            dedup_key = content.strip().lower()
            if dedup_key not in seen_contents:
                seen_contents.add(dedup_key)
                chunks.append({"content": content, "metadata": doc.metadata, "score": score})

    # lower cosine distance = more similar; sort ascending and cap
    chunks.sort(key=lambda c: c["score"])
    return {"retrieved_chunks": chunks[:RETRIEVAL_K]}