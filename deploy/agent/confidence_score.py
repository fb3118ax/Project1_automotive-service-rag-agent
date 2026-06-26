from agent.state import AgentState

def confidence_score (state):
    chunks = state["retrieved_chunks"]
    if not chunks:
        return {"confidence_score": 0.0, "citations": []}

    avg_distance = sum(chunk["score"] for chunk in chunks) / len(chunks)
    confidence = max(0.0, min(1.0, 1 - avg_distance))

    citation = []
    for chunk in chunks:
        citation.append({
                "page": chunk["metadata"].get("page_number"),
                
                "source": chunk["metadata"].get("source_file")
            })              
    return {"confidence_score" : confidence, "citations" : citation}