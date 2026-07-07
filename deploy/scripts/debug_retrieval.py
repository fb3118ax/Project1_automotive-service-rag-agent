"""
scripts/debug_retrieval.py

Calls the REAL text_retriever() and confidence_score() functions from the
pipeline directly — no guessing at Chroma internals, no assumptions about
a reranker (there isn't one in the text-only pipeline; text_retriever is
plain vector similarity across query + query_variations, deduped, sorted
by distance, capped to RETRIEVAL_K).

This shows you exactly what conversation.py would receive as `context`
and `citations` for a given query — useful for checking two separate
things that are easy to conflate:

  1. RETRIEVAL: did the expected page even get retrieved, and how did it
     rank by similarity score against competing chunks?
  2. GROUNDING: of the chunks retrieved (and therefore cited), does the
     final answer actually draw content from each one, or does a chunk
     just ride along in `citations` without meaningfully contributing to
     the generated text? (confidence_score.py currently cites every
     retrieved chunk unconditionally — this script won't tell you
     grounding is broken, but it lets you see the exact context blob the
     LLM sees, so you can eyeball whether a cited page's content is even
     in there.)

Usage (from deploy/, with PYTHONPATH set):
    $env:PYTHONPATH="."
    python scripts/debug_retrieval.py "how vehicle cockpit works ?" --page 36
    python scripts/debug_retrieval.py "how vehicle cockpit works ?" --variations "steering wheel controls" "cockpit layout"
"""
import argparse
from agent.retrievers import text_retriever
from agent.confidence_score import confidence_score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query", type=str, help="Query text to test retrieval for")
    parser.add_argument("--variations", nargs="*", default=[],
                         help="Optional query_variations, same as query_expansion would produce")
    parser.add_argument("--page", type=int, default=None,
                         help="Highlight this page number if present among retrieved chunks")
    args = parser.parse_args()

    state = {
        "query": args.query,
        "query_variations": args.variations,
    }

    retrieval_result = text_retriever(state)
    chunks = retrieval_result["retrieved_chunks"]

    state["retrieved_chunks"] = chunks
    conf_result = confidence_score(state)

    print(f"\nQuery: {args.query!r}")
    if args.variations:
        print(f"Query variations: {args.variations}")
    print(f"\nRetrieved {len(chunks)} chunks (post-dedup, capped to RETRIEVAL_K):\n")
    print(f"{'Rank':<5}{'Page':<7}{'Distance':<10}{'Preview'}")
    print("-" * 100)

    target_found = False
    for rank, chunk in enumerate(chunks, start=1):
        page = chunk["metadata"].get("page_number", "?")
        score = chunk["score"]
        preview = chunk["content"][:120].replace("\n", " ")
        marker = "  <-- TARGET" if args.page is not None and page == args.page else ""
        print(f"{rank:<5}{page:<7}{score:<10.4f}{preview}{marker}")
        if args.page is not None and page == args.page:
            target_found = True

    if args.page is not None:
        if target_found:
            match = next(c for c in chunks if c["metadata"].get("page_number") == args.page)
            print(f"\n[TARGET PAGE {args.page}] full retrieved content:\n{match['content']}")
        else:
            print(f"\n[TARGET PAGE {args.page}] NOT retrieved at all for this query.")

    print(f"\nConfidence score: {conf_result['confidence_score']:.4f}")
    print(f"Citations returned: {conf_result['citations']}")

    print("\n--- Exact context blob conversation.py would build ---\n")
    context = "\n\n".join([
        f"Page {c['metadata'].get('page_number', 'unknown')}:\n{c['content']}"
        for c in chunks
    ])
    print(context)


if __name__ == "__main__":
    main()
