"""
semantic_cache.py
-----------------
ChromaDB-backed semantic cache for MechAI.

- Cache lives in ./mechai_cache_db (separate from BMW_RAG_db)
- Keyed by: embed(query + user_type)
- Similarity threshold: > 0.95 (cosine)
- TTL: 30 days via cached_at metadata
- Stores: response, image_paths, image_captions, confidence_score, current_topic
"""

import json
import logging
from datetime import datetime, timedelta
import chromadb
from agent.state import AgentState
from config.settings import (
    CACHE_DB_PATH,
    CACHE_COLLECTION,
    CACHE_SIMILARITY_THRESHOLD,
    CACHE_TTL_DAYS,
    embedding_model,
)

logger = logging.getLogger(__name__)

# ── ChromaDB client ────────────────────────────────────────────────────────────
_client = chromadb.PersistentClient(path=CACHE_DB_PATH)
_collection = _client.get_or_create_collection(
    name=CACHE_COLLECTION,
    metadata={"hnsw:space": "cosine"},
)


def _embed(text: str) -> list[float]:
    return embedding_model.embed_query(text)


def _cache_key_text(query: str, user_type: str) -> str:
    """Canonical text used for embedding — query + user_type."""
    return f"{query.strip().lower()}|{user_type}"


def _is_expired(cached_at_iso: str) -> bool:
    cached_at = datetime.fromisoformat(cached_at_iso)
    return datetime.utcnow() - cached_at > timedelta(days=CACHE_TTL_DAYS)


# ── Public API ─────────────────────────────────────────────────────────────────

def check_cache(state: AgentState) -> AgentState:
    query = state["query"]
    user_type = state.get("user_type", "owner")

    try:
        vector = _embed(_cache_key_text(query, user_type))
        results = _collection.query(
            query_embeddings=[vector],
            n_results=1,
            include=["metadatas", "distances"],
        )

        if results["ids"][0]:
            distance = results["distances"][0][0]
            similarity = 1 - distance
            
            if similarity >= CACHE_SIMILARITY_THRESHOLD:
                meta = results["metadatas"][0][0]
                if _is_expired(meta["cached_at"]):
                    return {**state, "cache_hit": False}
                
                return {
                    **state,
                    "cache_hit": True,
                    "final_response":   meta["response"],
                    "image_paths":      json.loads(meta["image_paths"]),
                    "image_captions":   json.loads(meta["image_captions"]),
                    "confidence_score": float(meta["confidence_score"]),
                    "current_topic":    meta["current_topic"],
                }

    except Exception as e:        

        return {**state, "cache_hit": False}


def write_cache(state: AgentState) -> None:
    """
    Called from output_guardrail on a successful pipeline run.
    Writes response + metadata to the cache collection.
    """
    query = state["query"]
    user_type = state.get("user_type", "owner")

    try:
        vector = _embed(_cache_key_text(query, user_type))
        doc_id = f"{query.strip().lower()}|{user_type}"[:512]  

        _collection.upsert(
            ids=[doc_id],
            embeddings=[vector],
            documents=[doc_id],
            metadatas=[{
                "response":         state.get("final_response", ""),
                "image_paths":      json.dumps(state.get("image_paths", [])),
                "image_captions":   json.dumps(state.get("image_captions", [])),
                "confidence_score": str(state.get("confidence_score", 0.0)),
                "current_topic":    state.get("current_topic", ""),
                "cached_at":        datetime.utcnow().isoformat(),
            }],
        )
        logger.info(f"Cache WRITE for: {query!r}")

    except Exception as e:
        logger.warning(f"Cache write failed (non-fatal): {e}")
