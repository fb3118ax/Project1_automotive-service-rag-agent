from agent.state import AgentState

def confidence_score (state):
    chunks = state["retrieved_chunks"]
    if not chunks:
        return {"confidence_score": 0.0, "citations": []}
    avg_score = sum(chunk["score"] for chunk in chunks) / len(chunks)
        
    citation = []
    for chunk in chunks:
        citation.append({
                "page": chunk["metadata"].get("page_number"),
                # "section": chunk["metadata"].get("section"),
                "source": chunk["metadata"].get("source_file")
            })              
    return {"confidence_score" : avg_score, "citations" : citation}
   