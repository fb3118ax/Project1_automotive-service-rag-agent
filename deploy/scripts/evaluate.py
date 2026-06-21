"""
scripts/evaluate.py

Runs the MechAI pipeline against the generated testset and evaluates using RAGAS.
Scores: faithfulness, answer_relevancy, context_precision, context_recall
Posts per-sample RAGAS scores as feedback to LangSmith.

Usage:
    python scripts/evaluate.py

Requirements:
    pip install ragas langsmith
"""

import os
import json
import sys
import uuid
from dotenv import load_dotenv

load_dotenv()

# Add project root to path so agent imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.graph import app as agent_app
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from ragas.dataset_schema import SingleTurnSample, EvaluationDataset
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.runnables import RunnableConfig
from langsmith import Client as LangSmithClient

# RunConfig import varies by RAGAS version — handle both
try:
    from ragas.run_config import RunConfig
except ImportError:
    from ragas import RunConfig

# ── Config ────────────────────────────────────────────────────────────────────
TESTSET_PATH      = os.path.join(os.path.dirname(__file__), "testset.json")
OUTPUT_PATH       = os.path.join(os.path.dirname(__file__), "ragas_results.json")
LLM_MODEL         = os.getenv("LLM_MODEL", "gpt-4o")
EMBEDDING_MODEL   = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
USER_TYPE         = "technician"   # technician = full answers, better for eval

# LangSmith client — posts RAGAS scores as feedback on each traced run
langsmith_client = LangSmithClient(api_key=LANGCHAIN_API_KEY)


# ── Pipeline runner ───────────────────────────────────────────────────────────
def run_pipeline(question: str) -> dict:
    """
    Invoke the LangGraph agent exactly as the /query endpoint does.
    Captures run_id so RAGAS scores can be posted back to LangSmith as feedback.
    Returns: answer (str), retrieved_contexts (list[str]), run_id (str)
    """
    run_id = str(uuid.uuid4())
    config = RunnableConfig(run_id=run_id)

    result = agent_app.invoke({
        "query":                question,
        "user_type":            USER_TYPE,
        "query_variations":     [],
        "conversation_history": [],
        "intent":               "",
        "guardrail_status":     "",
        "guardrail_response":   "",
        "retrieved_chunks":     [],
        "confidence_score":     0.0,
        "citations":            [],
        "image_paths":          []
    }, config=config)

    # Extract answer — same logic as app.py
    if result["guardrail_status"] in ("blocked_input", "blocked_output"):
        answer = result["guardrail_response"]
    else:
        answer = result["conversation_history"][-1].content

    # Extract retrieved contexts — list of chunk content strings
    contexts = [chunk["content"] for chunk in result.get("retrieved_chunks", [])]

    # Strip appended warning before RAGAS evaluation
    answer = answer.split("\n\n⚠️ Note:")[0].strip()

    return {"answer": answer, "contexts": contexts, "run_id": run_id}


# ── Build RAGAS dataset ───────────────────────────────────────────────────────
def build_evaluation_dataset(testset: list[dict]) -> tuple[EvaluationDataset, list[str]]:
    """
    Runs pipeline for each question and builds RAGAS dataset.
    Also returns run_ids in same order as samples for LangSmith feedback.
    """
    samples  = []
    run_ids  = []

    for i, entry in enumerate(testset):
        print(f"  Running pipeline for Q{i+1}/{len(testset)}: {entry['question'][:60]}...")
        result = run_pipeline(entry["question"])

        if not result["contexts"]:
            print(f"  Warning: No contexts retrieved for Q{i+1} — skipping")
            continue

        sample = SingleTurnSample(
            user_input=entry["question"],
            response=result["answer"],
            retrieved_contexts=result["contexts"],
            reference=entry["ground_truth"],
        )
        samples.append(sample)
        run_ids.append(result["run_id"])

    print(f"\nBuilt evaluation dataset with {len(samples)} samples")
    return EvaluationDataset(samples=samples), run_ids


# ── Run RAGAS evaluation ──────────────────────────────────────────────────────
def run_evaluation(dataset: EvaluationDataset) -> dict:
    llm        = ChatOpenAI(model=LLM_MODEL, temperature=0)
    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)

    print("\nRunning RAGAS evaluation (this will make several LLM calls)...")
    results = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=llm,
        embeddings=embeddings,
        run_config=RunConfig(max_workers=2, timeout=120),
    )
    return results


# ── Post scores to LangSmith ──────────────────────────────────────────────────
def post_feedback_to_langsmith(results, run_ids: list[str]) -> None:
    """
    Post per-sample RAGAS scores as feedback on each LangSmith run.
    This links evaluation scores directly to the traces in the dashboard.
    """
    metrics = {
        "faithfulness":      results["faithfulness"],
        "answer_relevancy":  results["answer_relevancy"],
        "context_precision": results["context_precision"],
        "context_recall":    results["context_recall"],
    }

    print("\nPosting RAGAS scores to LangSmith...")
    for i, run_id in enumerate(run_ids):
        for metric_name, scores in metrics.items():
            # scores is a list (one per sample) in newer RAGAS versions
            score = scores[i] if isinstance(scores, list) else float(scores)
            if score is None:
                continue
            try:
                langsmith_client.create_feedback(
                    run_id=run_id,
                    key=metric_name,
                    score=float(score),
                    comment=f"RAGAS {metric_name} for Q{i+1}"
                )
            except Exception as e:
                print(f"  Warning: Could not post {metric_name} for run {run_id}: {e}")

    print(f"  Posted scores for {len(run_ids)} runs across {len(metrics)} metrics")


# ── Save + display results ────────────────────────────────────────────────────
def _to_scalar(val) -> float:
    """Handle both old (float) and new (list) RAGAS return formats."""
    if isinstance(val, list):
        valid = [v for v in val if v is not None]
        return round(sum(valid) / len(valid), 4) if valid else 0.0
    return round(float(val), 4)


def save_results(results, output_path: str) -> None:
    scores = {
        "faithfulness":      _to_scalar(results["faithfulness"]),
        "answer_relevancy":  _to_scalar(results["answer_relevancy"]),
        "context_precision": _to_scalar(results["context_precision"]),
        "context_recall":    _to_scalar(results["context_recall"]),
    }

    with open(output_path, "w") as f:
        json.dump(scores, f, indent=2)

    print("\n" + "=" * 60)
    print("RAGAS Evaluation Results — MechAI")
    print("=" * 60)
    print(f"  Faithfulness:       {scores['faithfulness']:.4f}")
    print(f"  Answer Relevancy:   {scores['answer_relevancy']:.4f}")
    print(f"  Context Precision:  {scores['context_precision']:.4f}")
    print(f"  Context Recall:     {scores['context_recall']:.4f}")
    print("=" * 60)
    print(f"Results saved to: {output_path}")


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("MechAI — RAGAS Evaluation")
    print("=" * 60)

    # Load testset
    if not os.path.exists(TESTSET_PATH):
        raise FileNotFoundError(f"Testset not found at {TESTSET_PATH}. Run generate_testset.py first.")

    with open(TESTSET_PATH, "r", encoding="utf-8") as f:
        testset = json.load(f)
    print(f"Loaded {len(testset)} test cases from testset.json\n")

    # Build dataset by running pipeline on each question — captures run_ids
    dataset, run_ids = build_evaluation_dataset(testset)

    if len(dataset.samples) == 0:
        raise RuntimeError("No valid samples to evaluate. Check your pipeline and ChromaDB.")

    # Run RAGAS
    results = run_evaluation(dataset)

    # Post per-sample scores to LangSmith as feedback
    post_feedback_to_langsmith(results, run_ids)

    # Save and display aggregate results
    save_results(results, OUTPUT_PATH)


if __name__ == "__main__":
    main()
