import sys
sys.path.insert(0, ".")
from agent.retrievers import text_retriever, image_retriever, _gather_image_candidates, _rerank_images

state = {
    "query": "show me the tire pressure warning light diagram",
    "query_variations": [],
    "current_topic": ""
}

text_result = text_retriever(state)
state.update(text_result)

candidates = _gather_image_candidates(state)
print("CANDIDATES FOUND:", [c["path"] for c in candidates])
for c in candidates:
    print(c["path"], "-", c["caption"][:150])

kept = _rerank_images(state["query"], candidates)
print("KEPT AFTER RERANK:", [c["path"] for c in kept])