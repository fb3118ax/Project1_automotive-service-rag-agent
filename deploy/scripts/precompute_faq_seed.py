"""
scripts/precompute_faq_seed.py

Precomputes answers for a curated set of "seed" FAQ questions and upserts them
into the Cosmos `faq_seed` container. These seed answers are used by the /faq
endpoint to pad the frequently-asked list up to 5 whenever fewer than 5 "real"
(usage-derived) questions qualify.

This is a MANUAL, one-off script — run it whenever captions/retrieval change.
It is not automated and is not triggered by deploy.

Each result is printed for manual review before you trust it.

Usage:
    python scripts/precompute_faq_seed.py

Requires:
    COSMOS_CONNECTION_STRING, OPENAI_API_KEY (and the usual agent env vars)
"""

import os
import re
import sys
from dotenv import load_dotenv

load_dotenv()

# Add project root to path so `agent` / `api` imports work.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.graph import app as agent_app
from api.app import ensure_cosmos_setup, get_container


SEED_QUESTIONS = [
    "How do I access the Integrated Owner's Handbook on the control display?",
    "Where exactly can I find my vehicle's production date?",
    "Can I drive the vehicle while a Remote Software Upgrade is installing?",
    "How do I manually switch on the standby state if the vehicle enters its rest state?",
    "Where are the physical and digital locations to find my Vehicle Identification Number (VIN)?",
]


def slugify(text: str) -> str:
    """Stable, human-readable slug used as the faq_seed document id."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:120]


def answer_question(question: str) -> dict:
    """Run one question through the agent, mirroring the /query input shape."""
    result = agent_app.invoke({
        "query":                question,
        "user_type":            "owner",
        "query_variations":     [],
        "conversation_history": [],
        "intent":               "",
        "guardrail_status":     "",
        "guardrail_response":   "",
        "retrieved_chunks":     [],
        "confidence_score":     0.0,
        "citations":            [],
        "current_topic":        "",
        "image_paths":          [],
        "image_captions":       [],
        "cache_hit":            False,
        "final_response":       "",
    })

    if result.get("cache_hit"):
        answer = result["final_response"]
    elif result.get("guardrail_status") in ("blocked_input", "blocked_output"):
        answer = result["guardrail_response"]
    else:
        answer = result["conversation_history"][-1].content

    return {
        "answer":           answer,
        "citations":        result.get("citations", []),
        "confidence_score": result.get("confidence_score", 0.0),
    }


def main() -> None:
    ensure_cosmos_setup()
    container = get_container("faq_seed")

    for i, question in enumerate(SEED_QUESTIONS, 1):
        print(f"\n{'=' * 70}\n[{i}/{len(SEED_QUESTIONS)}] {question}\n{'=' * 70}")
        res = answer_question(question)

        doc = {
            "id":               slugify(question),
            "question_text":    question,
            "answer":           res["answer"],
            "citations":        res["citations"],
            "confidence_score": res["confidence_score"],
        }

        print(f"confidence_score: {doc['confidence_score']}")
        print(f"citations: {doc['citations']}")
        print(f"answer:\n{doc['answer']}")

        container.upsert_item(doc)
        print(f"→ upserted faq_seed id={doc['id']}")

    print("\nDone. Review the printed answers above before trusting them.")


if __name__ == "__main__":
    main()
