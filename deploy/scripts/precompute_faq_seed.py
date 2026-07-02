"""
Manually rerun this script whenever captions/retrieval are updated,
so faq_seed answers reflect the current pipeline instead of a stale snapshot.

Usage (from repo root, with PYTHONPATH set):
    $env:PYTHONPATH="."
    python scripts/precompute_faq_seed.py
"""
import os
import re
from azure.cosmos import CosmosClient, PartitionKey, exceptions
from agent.graph import app as agent_app

COSMOS_CONNECTION_STRING = os.getenv("COSMOS_CONNECTION_STRING")
COSMOS_DATABASE = "mechai-db"
FAQSEED_CONTAINER = "faq_seed"

SEED_QUESTIONS = [
    "How do I access the Integrated Owner's Handbook on the control display?",
    "Where exactly can I find my vehicle's production date?",
    "Can I drive the vehicle while a Remote Software Upgrade is installing?",
    "How do I manually switch on the standby state if the vehicle enters its rest state?",
    "Where are the physical and digital locations to find my Vehicle Identification Number (VIN)?",
]


def slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'\s+', '-', slug)
    return slug[:60]


def get_faqseed_container():
    client = CosmosClient.from_connection_string(COSMOS_CONNECTION_STRING)
    db = client.get_database_client(COSMOS_DATABASE)
    try:
        container = db.get_container_client(FAQSEED_CONTAINER)
        container.read()
    except exceptions.CosmosResourceNotFoundError:
        container = db.create_container(
            id=FAQSEED_CONTAINER,
            partition_key=PartitionKey(path="/id"),
        )
    return container


def main():
    container = get_faqseed_container()

    for question in SEED_QUESTIONS:
        print(f"\n--- Running: {question}")

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
        elif result["guardrail_status"] in ("blocked_input", "blocked_output"):
            answer = result["guardrail_response"]
            print(f"  WARNING: guardrail triggered on seed question — review manually: {question}")
        else:
            answer = result["conversation_history"][-1].content

        doc = {
            "id": slugify(question),
            "question_text": question,
            "answer": answer,
            "citations": result.get("citations", []),
            "confidence_score": result.get("confidence_score", 0.0),
        }

        container.upsert_item(doc)

        print(f"  Confidence: {doc['confidence_score']}")
        print(f"  Citations: {doc['citations']}")
        print(f"  Answer preview: {answer[:150]}...")

    print("\nDone. Review the printed answers above before trusting them in production.")


if __name__ == "__main__":
    main()
