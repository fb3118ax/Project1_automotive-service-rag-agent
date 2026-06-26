import shutil
import chromadb
import hashlib
import os
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from config.settings import DB_PATH, EMBEDDING_MODEL


def _build_chunk_id(doc):
    """
    Deterministic ID per chunk, so re-running ingest.py WITHOUT --rebuild
    updates existing entries instead of inserting a second copy of every
    chunk.

    Why this matters: Chroma.from_documents() generates a random UUID per
    call when no ids are passed in. Run ingestion twice on the same manual
    without --rebuild and you get two copies of every chunk in the
    collection — same content, different random ID each time. Nothing
    crashes, but every later similarity search is quietly skewed: a
    duplicated chunk effectively gets double weight in the index, which can
    crowd a correct-but-only-inserted-once chunk out of the top-k results.

    Built from source file + page + image_path (empty for text chunks) +
    the chunk text itself, so re-ingesting the same chunk always produces
    the same ID, while two genuinely different chunks (even on the same
    page) still get different IDs.
    """
    key = "|".join([
        doc.metadata.get("source_file", ""),
        str(doc.metadata.get("page_number", "")),
        doc.metadata.get("image_path", ""),
        doc.page_content,
    ])
    return hashlib.md5(key.encode("utf-8")).hexdigest()


def vector_store(chunks, collection_name, persist_dir=DB_PATH, rebuild=False):
    if rebuild:
        try:
            import chromadb
            temp_client = chromadb.PersistentClient(path=persist_dir)
            temp_client.delete_collection(collection_name)
            print(f"Collection '{collection_name}' deleted.")
        except Exception as e:
            print(f"Collection delete skipped: {e}")

    embedding_model = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    ids = [_build_chunk_id(doc) for doc in chunks]
    store = Chroma.from_documents(
        documents=chunks,
        ids=ids,
        collection_name=collection_name,
        embedding=embedding_model,
        persist_directory=persist_dir,
        collection_metadata={"hnsw:space": 'cosine'}
    )
    print(f"Collection '{collection_name}' created with {len(chunks)} chunks.")
    return store