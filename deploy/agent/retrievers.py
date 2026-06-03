from config.settings import text_store, table_store
from agent.state import AgentState


def text_retriever(state):
    
    results = text_store.similarity_search_with_score(state["query"], k=5)
    chunks = []  
    for doc, score in results:
        chunks.append({ 
            "content": doc.page_content,
            "metadata": doc.metadata,
            "score": score
        })
    return {"retrieved_chunks": chunks}



def table_retriever(state):
    results = table_store.similarity_search_with_score(state["query"], k=5)
    chunks = []  
    for doc, score in results:
        chunks.append({ 
            "content": doc.page_content,
            "metadata": doc.metadata,
            "score": score
        })
    return {"retrieved_chunks": chunks}