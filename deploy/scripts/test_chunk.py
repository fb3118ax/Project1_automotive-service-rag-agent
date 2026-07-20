from config.settings import embedding_model, TEXT_COLLECTION, DB_PATH
from langchain_chroma import Chroma
import chromadb

client_db = chromadb.PersistentClient(path=DB_PATH)
text_store = Chroma(
    client=client_db,
    collection_name=TEXT_COLLECTION,
    embedding_function=embedding_model
)

results = text_store.get(where={"page_number": 22})
print(results['documents'])
print(results['metadatas'])

res = text_store.similarity_search_with_score("how to get in a car?", k=10)
for doc, score in res:
    print(score, doc.metadata.get("page_number"))