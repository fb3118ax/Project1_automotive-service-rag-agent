from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from agent.graph import app as agent_app
from langchain_core.messages import HumanMessage, AIMessage
from azure.cosmos import CosmosClient, PartitionKey, exceptions
from datetime import datetime
from collections import defaultdict
import logging
import re
import uuid
import os

logger = logging.getLogger("mechai.api")

# ── Rate Limiter ───────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

api = FastAPI()
api.state.limiter = limiter
api.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

api.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://project1-automotive-service-rag-age.vercel.app",
        "https://project1-automotive-service-rag-agent-etro5jdmh.vercel.app"
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Cosmos DB ─────────────────────────────────────────────────────────────────
# COSMOS_CONNECTION_STRING = os.getenv("COSMOS_CONNECTION_STRING")
# COSMOS_DATABASE          = "mechai-db"
# COSMOS_CONTAINER         = "sessions"

# cosmos_client    = CosmosClient.from_connection_string(COSMOS_CONNECTION_STRING)
# cosmos_database  = cosmos_client.get_database_client(COSMOS_DATABASE)
# cosmos_container = cosmos_database.get_container_client(COSMOS_CONTAINER)

# ── Cosmos DB (lazy init) ──────────────────────────────────────────────────
COSMOS_CONNECTION_STRING = os.getenv("COSMOS_CONNECTION_STRING")
COSMOS_DATABASE          = "mechai-db"
COSMOS_CONTAINER         = "sessions"

# 15 days, in seconds — applied to `sessions` and `query_log`.
SESSION_TTL_SECONDS   = 1296000
QUERY_LOG_TTL_SECONDS = 1296000

_cosmos_database   = None
_cosmos_containers = {}

def get_cosmos_database():
    global _cosmos_database
    if _cosmos_database is None:
        client = CosmosClient.from_connection_string(
            COSMOS_CONNECTION_STRING,
            connection_timeout=10,   # seconds to establish connection
            request_timeout=30,      # seconds to wait for a response
        )
        _cosmos_database = client.get_database_client(COSMOS_DATABASE)
    return _cosmos_database


def get_container(name: str):
    """Return a (cached) container client by name."""
    if name not in _cosmos_containers:
        _cosmos_containers[name] = get_cosmos_database().get_container_client(name)
    return _cosmos_containers[name]


def get_cosmos_container():
    """Handle to the `sessions` container (kept for backwards compatibility)."""
    return get_container(COSMOS_CONTAINER)


def ensure_cosmos_setup() -> None:
    """Idempotently create the containers this app relies on and make sure the
    TTL settings match. Safe to call repeatedly; never raises."""
    try:
        db = get_cosmos_database()

        # query_log — partitioned by user_id, 15-day TTL.
        db.create_container_if_not_exists(
            id="query_log",
            partition_key=PartitionKey(path="/user_id"),
            default_ttl=QUERY_LOG_TTL_SECONDS,
        )
        # faq_seed — partitioned by id, permanent (no TTL).
        db.create_container_if_not_exists(
            id="faq_seed",
            partition_key=PartitionKey(path="/id"),
        )
        # sessions — should already exist; ensure the 15-day TTL is set.
        sessions = db.create_container_if_not_exists(
            id=COSMOS_CONTAINER,
            partition_key=PartitionKey(path="/id"),
            default_ttl=SESSION_TTL_SECONDS,
        )
        props = sessions.read()
        if props.get("defaultTtl") != SESSION_TTL_SECONDS:
            db.replace_container(
                sessions,
                partition_key=PartitionKey(path="/id"),
                default_ttl=SESSION_TTL_SECONDS,
            )
    except Exception as exc:
        logger.warning("ensure_cosmos_setup failed: %s", exc)


@api.on_event("startup")
def _startup_cosmos():
    ensure_cosmos_setup()


# ── Session helpers ───────────────────────────────────────────────────────────
def serialize_history(history: list) -> list:
    """Convert LangChain messages to JSON-serializable dicts."""
    result = []
    for m in history:
        if isinstance(m, HumanMessage):
            result.append({"role": "human", "content": m.content})
        elif isinstance(m, AIMessage):
            result.append({"role": "ai", "content": m.content})
    return result


def deserialize_history(history: list) -> list:
    """Convert JSON dicts back to LangChain messages."""
    result = []
    for m in history:
        if m["role"] == "human":
            result.append(HumanMessage(content=m["content"]))
        elif m["role"] == "ai":
            result.append(AIMessage(content=m["content"]))
    return result


def _first_human_content(history: list) -> str:
    """First human message content, truncated to 80 chars — used as a preview."""
    for m in history:
        if isinstance(m, HumanMessage):
            return (m.content or "")[:80]
    return ""


def get_session(session_key: str) -> tuple[list, str]:
    try:
        item = get_cosmos_container().read_item(item=session_key, partition_key=session_key)
        return deserialize_history(item.get("history", [])), item.get("current_topic", "")
    except exceptions.CosmosResourceNotFoundError:
        return [], ""
    except Exception:
        return [], ""

def save_session(
    session_key: str,
    history: list,
    current_topic: str,
    user_id: str = "",
    user_type: str = "",
    session_id: str = "",
) -> None:
    try:
        container = get_cosmos_container()

        # Preserve first_query set on an earlier turn; only compute it on first write.
        first_query = _first_human_content(history)
        try:
            existing = container.read_item(item=session_key, partition_key=session_key)
            if existing.get("first_query"):
                first_query = existing["first_query"]
        except exceptions.CosmosResourceNotFoundError:
            pass

        container.upsert_item({
            "id":            session_key,
            "session_key":   session_key,
            "session_id":    session_id,
            "user_id":       user_id,
            "user_type":     user_type,
            "history":       serialize_history(history),
            "current_topic": current_topic,
            "timestamp":     datetime.utcnow().isoformat(),
            "first_query":   first_query,
        })
    except Exception:
        pass


# ── Query-log + FAQ helpers ───────────────────────────────────────────────────
def normalize_query(text: str) -> str:
    """Lowercase, trim, strip punctuation (keep alphanumerics + spaces), collapse
    runs of whitespace to a single space."""
    text = (text or "").lower().strip()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def log_query(user_id: str, session_id: str, user_type: str, query_text: str) -> None:
    """Append a query to the `query_log` container. Never raises."""
    try:
        get_container("query_log").upsert_item({
            "id":                     str(uuid.uuid4()),
            "user_id":                user_id,
            "session_id":             session_id,
            "user_type":              user_type,
            "query_text_raw":         query_text,
            "query_text_normalized":  normalize_query(query_text),
            "timestamp":              datetime.utcnow().isoformat(),
        })
    except Exception as exc:
        logger.warning("log_query failed: %s", exc)


# ── Request / Response ────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    query: str
    session_id: str
    user_type: str
    user_id: str


class QueryResponse(BaseModel):
    answer: str
    citations: list
    confidence_score: float
    guardrail_response: str


# ── Query endpoint ────────────────────────────────────────────────────────────
@api.post("/query")
@limiter.limit("5/minute")
async def query(request: Request, body: QueryRequest):
    session_key = f"{body.session_id}_{body.user_type}"

    # Log every query regardless of guardrail outcome (one per request).
    log_query(body.user_id, body.session_id, body.user_type, body.query)

    conversation_history, current_topic = get_session(session_key)
    result = agent_app.invoke({
        "query":                body.query,
        "user_type":            body.user_type,
        "query_variations":     [],
        "conversation_history": conversation_history,
        "intent":               "",
        "guardrail_status":     "",
        "guardrail_response":   "",
        "retrieved_chunks":     [],
        "confidence_score":     0.0,
        "citations":            [],
        "current_topic":        current_topic,
        "image_paths":          [],
        "image_captions":       [],
        "cache_hit":            False,
        "final_response":       "",
    })

    if result.get("cache_hit"):
        last_message = result["final_response"]
        save_session(session_key, result["conversation_history"], result.get("current_topic", ""),
                     body.user_id, body.user_type, body.session_id)
    elif result["guardrail_status"] == "blocked_input":
        last_message = result["guardrail_response"]
    elif result["guardrail_status"] == "blocked_output":
        last_message = result["guardrail_response"]
        save_session(session_key, result["conversation_history"], result.get("current_topic", ""),
                     body.user_id, body.user_type, body.session_id)
    else:
        last_message = result["conversation_history"][-1].content
        save_session(session_key, result["conversation_history"], result.get("current_topic", ""),
                     body.user_id, body.user_type, body.session_id)

    return QueryResponse(
        answer=last_message,
        citations=result["citations"],
        confidence_score=result["confidence_score"],
        guardrail_response=result["guardrail_response"],
    )


# ── History endpoints ─────────────────────────────────────────────────────────
@api.get("/sessions")
async def list_sessions(user_id: str):
    """Recent conversations for a user (partition-scoped, newest first, max 20)."""
    try:
        container = get_cosmos_container()
        query_text = (
            "SELECT c.id, c.session_key, c.session_id, c.user_type, c.timestamp, "
            "c.first_query FROM c WHERE c.user_id = @user_id "
            "ORDER BY c.timestamp DESC"
        )
        items = container.query_items(
            query=query_text,
            parameters=[{"name": "@user_id", "value": user_id}],
            partition_key=user_id,
            max_item_count=20,
        )
        results = []
        for doc in items:
            session_id = doc.get("session_id")
            if not session_id:
                # Legacy docs: id/session_key is "{session_id}_{user_type}".
                key = doc.get("session_key") or doc.get("id") or ""
                suffix = f"_{doc.get('user_type', '')}"
                session_id = key[: -len(suffix)] if suffix != "_" and key.endswith(suffix) else key
            results.append({
                "session_id": session_id,
                "user_type":  doc.get("user_type"),
                "timestamp":  doc.get("timestamp"),
                "preview":    doc.get("first_query"),
            })
            if len(results) >= 20:
                break
        return results
    except Exception as exc:
        logger.warning("list_sessions failed: %s", exc)
        return []


@api.get("/sessions/{session_id}")
async def get_session_history(session_id: str, user_id: str, user_type: str):
    """Full history for a past conversation, ready for the frontend to resume."""
    session_key = f"{session_id}_{user_type}"
    history, _ = get_session(session_key)
    return {"history": serialize_history(history)}


@api.get("/faq")
async def get_faq():
    """Top questions by frequency, padded with curated seed questions to 5."""
    real_entries = []
    try:
        rows = get_container("query_log").query_items(
            query="SELECT c.query_text_raw, c.query_text_normalized, c.timestamp FROM c",
            enable_cross_partition_query=True,
        )
        groups: dict = defaultdict(lambda: {"count": 0, "raw": "", "timestamp": ""})
        for row in rows:
            norm = row.get("query_text_normalized", "")
            if not norm:
                continue
            g = groups[norm]
            g["count"] += 1
            ts = row.get("timestamp", "")
            if ts >= g["timestamp"]:
                g["timestamp"] = ts
                g["raw"] = row.get("query_text_raw", "")

        qualifying = [
            {"norm": norm, "question": g["raw"], "count": g["count"]}
            for norm, g in groups.items()
            if g["count"] >= 3
        ]
        qualifying.sort(key=lambda e: e["count"], reverse=True)
        real_entries = qualifying[:5]
    except Exception as exc:
        logger.warning("get_faq real-entry aggregation failed: %s", exc)

    faq = [{"question": e["question"], "source": "real"} for e in real_entries]
    included_norms = {e["norm"] for e in real_entries}

    if len(faq) < 5:
        try:
            seeds = get_container("faq_seed").query_items(
                query="SELECT * FROM c",
                enable_cross_partition_query=True,
            )
            for seed in seeds:
                if len(faq) >= 5:
                    break
                question = seed.get("question_text") or seed.get("question", "")
                if normalize_query(question) in included_norms:
                    continue
                faq.append({
                    "question":         question,
                    "answer":           seed.get("answer", ""),
                    "citations":        seed.get("citations", []),
                    "confidence_score": seed.get("confidence_score", 0.0),
                    "source":           "seed",
                })
        except Exception as exc:
            logger.warning("get_faq seed padding failed: %s", exc)

    return faq