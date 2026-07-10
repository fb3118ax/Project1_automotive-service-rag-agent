from agent.state import AgentState

def confidence_score(state):
    chunks = state["retrieved_chunks"]
    if not chunks:
        return {"confidence_score": 0.0, "citations": []}

    # Top-2 only, rank-weighted. Using all K chunks let weak fill-in matches
    # (rank 3/4, often loosely related) drag the score down even when rank-1
    # was a strong hit. Confidence should reflect "how good is the best
    # evidence," not "average quality across everything retrieved."
    top2 = sorted(chunks, key=lambda c: c["score"])[:2]
    weights = [1 / (i + 1) for i in range(len(top2))]
    weighted_avg_distance = sum(c["score"] * w for c, w in zip(top2, weights)) / sum(weights)
    confidence = max(0.0, min(1.0, 1 - weighted_avg_distance))

    citation = []
    for chunk in chunks:
        citation.append({
            "page": chunk["metadata"].get("page_number"),
            "source": chunk["metadata"].get("source_file")
        })
    return {"confidence_score": confidence, "citations": citation}