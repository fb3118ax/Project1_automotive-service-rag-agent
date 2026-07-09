from agent.state import AgentState

def confidence_score (state):
    chunks = state["retrieved_chunks"]
    if not chunks:
        return {"confidence_score": 0.0, "citations": []}

    # Rank-weighted average, not a flat mean. text_retriever pools candidates across
    # every query variation, then caps to RETRIEVAL_K by distance — so when only 1-2
    # chunks are genuinely strong matches, the remaining slots still get filled with
    # whatever ranked next, even if it's only loosely related. A flat average lets
    # those weaker fill-in chunks pull the score down by as much as the strong
    # matches pull it up. Weighting by rank (1, 1/2, 1/3, ...) keeps the best match
    # dominant while still letting weaker supporting chunks contribute proportionally
    # less, rather than being silently dropped or counted equally.
    distances = sorted(chunk["score"] for chunk in chunks)
    weights = [1 / (i + 1) for i in range(len(distances))]
    weighted_avg_distance = sum(d * w for d, w in zip(distances, weights)) / sum(weights)
    confidence = max(0.0, min(1.0, 1 - weighted_avg_distance))

    citation = []
    for chunk in chunks:
        citation.append({
                "page": chunk["metadata"].get("page_number"),
                
                "source": chunk["metadata"].get("source_file")
            })              
    return {"confidence_score" : confidence, "citations" : citation}