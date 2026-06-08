import shutil
import chromadb
import os
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from config.settings import DB_PATH, EMBEDDING_MODEL


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
    store = Chroma.from_documents(
        documents=chunks,
        collection_name=collection_name,
        embedding=embedding_model,
        persist_directory=persist_dir,
        collection_metadata={"hnsw:space": 'cosine'}
    )
    print(f"Collection '{collection_name}' created with {len(chunks)} chunks.")
    return store