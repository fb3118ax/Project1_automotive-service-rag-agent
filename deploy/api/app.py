from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from agent.graph import app as agent_app
from langchain_core.messages import HumanMessage, AIMessage
from azure.cosmos import CosmosClient, exceptions, PartitionKey
from datetime import datetime, timezone
from config.settings import (DEMO_CREDENTIALS, MAX_LOGIN_ATTEMPTS, LOCKOUT_SECONDS, FAQ_SLOTS, FAQ_MIN_COUNT, COSMOS_CONNECTION_STRING, COSMOS_DATABASE, SESSIONS_CONTAINER, QUERYLOG_CONTAINER, SESSION_TTL_SECONDS, QUERYLOG_TTL_SECONDS)
import re
import uuid
import time

# ── Rate Limiter ───────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

api = FastAPI()
api.state.limiter = limiter
api.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

api.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://mech-ai-automotive-service-intelli.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Cosmos DB (lazy init) ──────────────────────────────────────────────────
COSMOS_CONNECTION_STRING = COSMOS_CONNECTION_STRING
COSMOS_DATABASE          = COSMOS_DATABASE

SESSIONS_CONTAINER  = SESSIONS_CONTAINER
QUERYLOG_CONTAINER  = QUERYLOG_CONTAINER

SESSION_TTL_SECONDS   = SESSION_TTL_SECONDS
QUERYLOG_TTL_SECONDS  = QUERYLOG_TTL_SECONDS  # 15 days

_cosmos_db = None
_containers = {}


def get_cosmos_db():
    global _cosmos_db
    if _cosmos_db is None:
        client = CosmosClient.from_connection_string(
            COSMOS_CONNECTION_STRING,
            connection_timeout=10,
            request_timeout=30,
        )
        _cosmos_db = client.get_database_client(COSMOS_DATABASE)
    return _cosmos_db


def get_container(name: str, partition_key_path: str, default_ttl: int | None = None):
    """Lazily fetch (and create if missing) a container, cached after first call."""
    if name in _containers:
        return _containers[name]

    db = get_cosmos_db()
    try:
        container = db.get_container_client(name)
        container.read()  # forces a check that it exists
    except exceptions.CosmosResourceNotFoundError:
        create_kwargs = {"id": name, "partition_key": PartitionKey(path=partition_key_path)}
        if default_ttl is not None:
            create_kwargs["default_ttl"] = default_ttl
        container = db.create_container(**create_kwargs)

    _containers[name] = container
    return container


def get_sessions_container():
    return get_container(SESSIONS_CONTAINER, "/session_key", default_ttl=SESSION_TTL_SECONDS)


def get_querylog_container():
    return get_container(QUERYLOG_CONTAINER, "/user_id", default_ttl=QUERYLOG_TTL_SECONDS)


# ── Session helpers ───────────────────────────────────────────────────────────
def serialize_history(history: list) -> list:
    """Convert LangChain messages to JSON-serializable dicts.
    AI messages carry citations + confidence_score so resumed conversations
    can re-render badges/citations, not just plain text."""
    result = []
    for m in history:
        if isinstance(m, HumanMessage):
            result.append({"role": "human", "content": m.content})
        elif isinstance(m, AIMessage):
            meta = getattr(m, "additional_kwargs", {}) or {}
            result.append({
                "role": "ai",
                "content": m.content,
                "citations": meta.get("citations", []),
                "confidence_score": meta.get("confidence_score"),
            })
    return result


def deserialize_history(history: list) -> list:
    """Convert JSON dicts back to LangChain messages, preserving citations/confidence
    in additional_kwargs so they survive a round trip through Cosmos."""
    result = []
    for m in history:
        if m["role"] == "human":
            result.append(HumanMessage(content=m["content"]))
        elif m["role"] == "ai":
            result.append(AIMessage(
                content=m["content"],
                additional_kwargs={
                    "citations": m.get("citations", []),
                    "confidence_score": m.get("confidence_score"),
                }
            ))
    return result


def get_session(session_key: str) -> tuple[list, str]:
    try:
        container = get_sessions_container()
        item = container.read_item(item=session_key, partition_key=session_key)
        return deserialize_history(item.get("history", [])), item.get("current_topic", "")
    except exceptions.CosmosResourceNotFoundError:
        return [], ""
    except Exception as e:
        print(f"[get_session] Cosmos read failed for {session_key}: {e}")
        return [], ""


def save_session(session_key: str, history: list, current_topic: str,
                  user_id: str, session_id: str, user_type: str) -> None:
    try:
        container = get_sessions_container()
        serialized = serialize_history(history)

        # preserve first_query across turns instead of overwriting it every save
        first_query = None
        try:
            existing = container.read_item(item=session_key, partition_key=session_key)
            first_query = existing.get("first_query")
        except exceptions.CosmosResourceNotFoundError:
            pass

        if not first_query:
            first_human = next((h["content"] for h in serialized if h["role"] == "human"), "")
            first_query = first_human[:80]

        container.upsert_item({
            "id":             session_key,
            "session_key":    session_key,
            "session_id":     session_id,
            "user_id":        user_id,
            "user_type":      user_type,
            "history":        serialized,
            "current_topic":  current_topic,
            "first_query":    first_query,
            "timestamp":      datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        print(f"[save_session] Cosmos write failed for {session_key}: {e}")


# ── Query log / FAQ helpers ───────────────────────────────────────────────────
def normalize_query(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def log_query(user_id: str, session_id: str, user_type: str, query_text: str) -> None:
    try:
        container = get_querylog_container()
        container.upsert_item({
            "id":                    str(uuid.uuid4()),
            "user_id":               user_id,
            "session_id":            session_id,
            "user_type":             user_type,
            "query_text_raw":        query_text,
            "query_text_normalized": normalize_query(query_text),
            "timestamp":             datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        print(f"[log_query] Cosmos write failed for user {user_id}: {e}")


# ── Demo login (UI-gate only, not real auth) ──────────────────────────────────
_login_attempts: dict[str, dict] = {}  # username -> {"count": int, "locked_until": float}


class LoginRequest(BaseModel):
    user_type: str
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    token: str | None = None
    message: str


@api.post("/auth/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    now = time.time()
    record = _login_attempts.get(body.username, {"count": 0, "locked_until": 0})

    if record["locked_until"] > now:
        remaining = int(record["locked_until"] - now)
        return LoginResponse(success=False, message=f"Account locked. Try again in {remaining}s.")

    creds = DEMO_CREDENTIALS.get(body.user_type)
    if not creds or body.username != creds["username"] or body.password != creds["password"]:
        record["count"] += 1
        if record["count"] >= MAX_LOGIN_ATTEMPTS:
            record["locked_until"] = now + LOCKOUT_SECONDS
            record["count"] = 0
            _login_attempts[body.username] = record
            return LoginResponse(success=False, message="Too many failed attempts. Locked for 2 minutes.")
        _login_attempts[body.username] = record
        return LoginResponse(success=False, message=f"Invalid credentials. {MAX_LOGIN_ATTEMPTS - record['count']} attempt(s) left.")

    _login_attempts.pop(body.username, None)
    token = str(uuid.uuid4())
    return LoginResponse(success=True, token=token, message="Login successful")


# ── Request / Response models ─────────────────────────────────────────────────
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


class SessionSummary(BaseModel):
    session_id: str
    user_type: str
    timestamp: str
    preview: str


class SessionHistoryResponse(BaseModel):
    history: list


class FaqItem(BaseModel):
    question: str


# ── Query endpoint ────────────────────────────────────────────────────────────
@api.post("/query")
@limiter.limit("5/minute")
async def query(request: Request, body: QueryRequest):
    session_key = f"{body.session_id}_{body.user_type}"

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
        "cache_hit":            False,
        "final_response":       "",
    })

    # FIX: log_query moved here and gated on guardrail_status != "blocked_input".
    # Previously it ran unconditionally before the guardrail check, so empty
    # queries, greetings, off-topic, profanity, and injection attempts were
    # all being written to query_log and could surface as "top" FAQs.
    if result["guardrail_status"] != "blocked_input":
        log_query(body.user_id, body.session_id, body.user_type, body.query)

    def _save():
        save_session(
            session_key, result["conversation_history"], result.get("current_topic", ""),
            body.user_id, body.session_id, body.user_type,
        )

    if result.get("cache_hit"):
        last_message = result["final_response"]
        _save()
    elif result["guardrail_status"] == "blocked_input":
        last_message = result["guardrail_response"]
    elif result["guardrail_status"] == "blocked_output":
        last_message = result["guardrail_response"]
        _save()
    else:
        last_message = result["conversation_history"][-1].content
        _save()

    return QueryResponse(
        answer=last_message,
        citations=result["citations"],
        confidence_score=result["confidence_score"],
        guardrail_response=result["guardrail_response"],
    )


# ── History endpoints ─────────────────────────────────────────────────────────
@api.get("/sessions", response_model=list[SessionSummary])
async def list_sessions(user_id: str, user_type: str):
    try:
        container = get_sessions_container()
        query_text = (
            "SELECT c.session_id, c.user_type, c.timestamp, c.first_query "
            "FROM c WHERE c.user_id = @user_id AND c.user_type = @user_type "
            "ORDER BY c.timestamp DESC"
        )
        items = list(container.query_items(
            query=query_text,
            parameters=[
                {"name": "@user_id", "value": user_id},
                {"name": "@user_type", "value": user_type},
            ],
            enable_cross_partition_query=True,
        ))[:20]

        return [
            SessionSummary(
                session_id=it.get("session_id", ""),
                user_type=it.get("user_type", ""),
                timestamp=it.get("timestamp", ""),
                preview=it.get("first_query", ""),
            )
            for it in items
        ]
    except Exception as e:
        print(f"[list_sessions] failed for user {user_id}: {e}")
        return []


@api.get("/sessions/{session_id}", response_model=SessionHistoryResponse)
async def get_session_history(session_id: str, user_id: str, user_type: str):
    session_key = f"{session_id}_{user_type}"
    history, _ = get_session(session_key)

    serialized = []
    for m in history:
        if isinstance(m, HumanMessage):
            serialized.append({"role": "human", "content": m.content})
        elif isinstance(m, AIMessage):
            meta = getattr(m, "additional_kwargs", {}) or {}
            serialized.append({
                "role": "ai",
                "content": m.content,
                "citations": meta.get("citations", []),
                "confidence_score": meta.get("confidence_score"),
            })

    if not serialized:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionHistoryResponse(history=serialized)


# ── FAQ endpoint ───────────────────────────────────────────────────────────────
FAQ_MIN_COUNT = FAQ_MIN_COUNT
FAQ_SLOTS = FAQ_SLOTS


@api.get("/faq", response_model=list[FaqItem])
async def get_faq():
    real_items: list[FaqItem] = []

    try:
        container = get_querylog_container()
        items = list(container.query_items(
            query="SELECT c.query_text_raw, c.query_text_normalized FROM c",
            enable_cross_partition_query=True,
        ))

        counts: dict[str, dict] = {}
        for it in items:
            norm = it.get("query_text_normalized", "")
            if not norm:
                continue
            if norm not in counts:
                counts[norm] = {"count": 0, "raw": it.get("query_text_raw", norm)}
            counts[norm]["count"] += 1
            counts[norm]["raw"] = it.get("query_text_raw", counts[norm]["raw"])  # most recent wins

        qualifying = [
            (norm, data) for norm, data in counts.items() if data["count"] >= FAQ_MIN_COUNT
        ]
        qualifying.sort(key=lambda x: x[1]["count"], reverse=True)

        for norm, data in qualifying[:FAQ_SLOTS]:
            real_items.append(FaqItem(question=data["raw"]))
    except Exception as e:
        print(f"[get_faq] query_log aggregation failed: {e}")

    return real_items[:FAQ_SLOTS]