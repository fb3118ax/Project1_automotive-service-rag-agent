from config.settings import RETRIEVAL_K, embedding_model, TABLE_COLLECTION, TEXT_COLLECTION,DB_PATH
from agent.state import AgentState
from langchain_chroma import Chroma
import chromadb


client_db = chromadb.PersistentClient(path=DB_PATH)

text_store = Chroma(
    client=client_db,
    collection_name=TEXT_COLLECTION,
    embedding_function=embedding_model
)

table_store = Chroma(
    client=client_db,
    collection_name=TABLE_COLLECTION,
    embedding_function=embedding_model
)
 
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
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": score
                })
    
    return {"retrieved_chunks": chunks}



def table_retriever(state):
    seen_contents = set()
    chunks = []
    all_queries = [state["query"]] + state["query_variations"]
    for query in all_queries:
        results = table_store.similarity_search_with_score(query, k=RETRIEVAL_K)
        for doc, score in results:
            if doc.page_content not in seen_contents:
                seen_contents.add(doc.page_content)
                chunks.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": score
                })
    
    return {"retrieved_chunks": chunks}