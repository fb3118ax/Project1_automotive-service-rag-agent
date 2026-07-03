import chromadb
from config.settings import DB_PATH, IMAGE_COLLECTION, EMBEDDING_MODEL
from langchain_openai import OpenAIEmbeddings
import sys

client = chromadb.PersistentClient(path=DB_PATH)
col = client.get_collection(IMAGE_COLLECTION)

embeddings =  OpenAIEmbeddings(model=EMBEDDING_MODEL)
# query_vec = embeddings.embed_query("what do the numbers on the steering wheel diagram mean")
query_text = sys.argv[1] if len(sys.argv) > 1 else "what do the numbers on the steering wheel diagram mean"
print(f"Query: {query_text}\n")
query_vec = embeddings.embed_query(query_text)

results = col.query(query_embeddings=[query_vec], n_results=5, include=["documents", "metadatas", "distances"])
for id_, doc, meta, dist in zip(results["ids"][0], results["documents"][0], results["metadatas"][0], results["distances"][0]):
    score = 1 - dist
    print(f"{score:.4f} | {meta.get('image_path')} | {doc[:70]}")
