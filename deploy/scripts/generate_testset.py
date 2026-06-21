"""
scripts/generate_testset.py

Pulls text chunks from ChromaDB and generates synthetic Q&A pairs using GPT-4o.
Output: scripts/testset.json — used as input for evaluate.py

Usage:
    python scripts/generate_testset.py
"""

import os
import json
import random
from dotenv import load_dotenv
from openai import OpenAI
import chromadb

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
DB_PATH           = os.getenv("CHROMA_DB_PATH", "./BMW_RAG_db")
TEXT_COLLECTION   = os.getenv("TEXT_COLLECTION", "text_chunks")
LLM_MODEL         = os.getenv("LLM_MODEL", "gpt-4o")
NUM_SAMPLES       = 10          # number of Q&A pairs to generate
OUTPUT_PATH       = os.path.join(os.path.dirname(__file__), "testset.json")
RANDOM_SEED       = 42

# ── Prompt ────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an automotive technical expert reviewing BMW service manual content.
Given a passage from a BMW service manual, generate one realistic question a BMW technician 
or owner might ask, along with a precise ground truth answer drawn strictly from the passage.

Rules:
- The question must be answerable ONLY from the given passage — no external knowledge
- The ground truth answer must be factually grounded in the passage text
- Keep the answer concise (2-4 sentences max)
- Do not reference "the passage" or "the text" in your output

Respond ONLY in this JSON format (no markdown, no preamble):
{
  "question": "...",
  "ground_truth": "..."
}"""

# ── Main ─────────────────────────────────────────────────────────────────────
def load_chunks_from_chroma(db_path: str, collection_name: str) -> list[dict]:
    """Pull all chunks from ChromaDB text_chunks collection."""
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_collection(collection_name)
    results = collection.get(include=["documents", "metadatas"])
    
    chunks = []
    for doc, meta in zip(results["documents"], results["metadatas"]):
        chunks.append({"text": doc, "metadata": meta})
    
    print(f"Loaded {len(chunks)} chunks from '{collection_name}'")
    return chunks


def sample_chunks(chunks: list[dict], n: int, seed: int) -> list[dict]:
    """Random sample of n chunks — reproducible via seed."""
    random.seed(seed)
    sampled = random.sample(chunks, min(n, len(chunks)))
    print(f"Sampled {len(sampled)} chunks for test set generation")
    return sampled


def generate_qa_pair(client: OpenAI, chunk_text: str) -> dict | None:
    """Call GPT-4o to generate a Q&A pair from a single chunk."""
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Passage:\n{chunk_text}"}
            ]
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if GPT-4o wraps response despite instructions
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        if not raw:
            print(f"  Empty response from GPT-4o — chunk likely too short or non-textual")
            return None
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  JSON parse error: {e} — raw: {repr(raw[:200])}")
        return None
    except Exception as e:
        print(f"  API error: {e} — skipping chunk")
        return None


def build_testset(chunks: list[dict], openai_client: OpenAI) -> list[dict]:
    """Generate Q&A pairs for all sampled chunks."""
    testset = []

    for i, chunk in enumerate(chunks):
        meta = chunk["metadata"]
        # Try common page key variants
        page = meta.get("page_number") or "?"
        print(f"  Generating pair {i+1}/{len(chunks)} (page {page})...")

        qa = generate_qa_pair(openai_client, chunk["text"])
        if qa is None:
            continue

        testset.append({
            "question":     qa["question"],
            "ground_truth": qa["ground_truth"],
            "context":      chunk["text"],
            "page":         page,
            "source":       meta.get("source_file", None),
        })

    print(f"\nGenerated {len(testset)} valid Q&A pairs")
    return testset


def save_testset(testset: list[dict], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(testset, f, indent=2, ensure_ascii=False)
    print(f"Testset saved to: {path}")


def main():
    print("=" * 60)
    print("MechAI — RAGAS Testset Generator")
    print("=" * 60)

    # Load chunks from ChromaDB
    chunks = load_chunks_from_chroma(DB_PATH, TEXT_COLLECTION)
    if not chunks:
        raise RuntimeError(f"No chunks found in '{TEXT_COLLECTION}'. Run ingestion first.")

    # Sample
    sampled = sample_chunks(chunks, NUM_SAMPLES, RANDOM_SEED)

    # Generate Q&A pairs
    openai_client = OpenAI()
    print(f"\nGenerating Q&A pairs using {LLM_MODEL}...")
    testset = build_testset(sampled, openai_client)

    if not testset:
        raise RuntimeError("No Q&A pairs generated. Check your OpenAI API key and ChromaDB.")

    # Save
    save_testset(testset, OUTPUT_PATH)

    # Preview
    print("\n── Sample Entry ──────────────────────────────────────")
    sample = testset[0]
    print(f"Q:  {sample['question']}")
    print(f"A:  {sample['ground_truth']}")
    print(f"Pg: {sample['page']}")
    print("=" * 60)


if __name__ == "__main__":
    main()