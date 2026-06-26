from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from agent.graph import app as agent_app
from langchain_core.messages import HumanMessage, AIMessage
from azure.cosmos import CosmosClient, exceptions
import os

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
COSMOS_CONNECTION_STRING = os.getenv("COSMOS_CONNECTION_STRING")
COSMOS_DATABASE          = "mechai-db"
COSMOS_CONTAINER         = "sessions"

cosmos_client    = CosmosClient.from_connection_string(COSMOS_CONNECTION_STRING)
cosmos_database  = cosmos_client.get_database_client(COSMOS_DATABASE)
cosmos_container = cosmos_database.get_container_client(COSMOS_CONTAINER)


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


def get_session(session_key: str) -> tuple[list, str]:
    try:
        item = cosmos_container.read_item(item=session_key, partition_key=session_key)
        return deserialize_history(item.get("history", [])), item.get("current_topic", "")
    except exceptions.CosmosResourceNotFoundError:
        return [], ""
    except Exception:
        return [], ""

def save_session(session_key: str, history: list, current_topic: str) -> None:
    try:
        cosmos_container.upsert_item({
            "id":            session_key,
            "session_key":   session_key,
            "history":       serialize_history(history),
            "current_topic": current_topic
        })
    except Exception:
        pass


# ── Request / Response ────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    query: str
    session_id: str
    user_type: str


class QueryResponse(BaseModel):
    answer: str
    citations: list
    confidence_score: float
    guardrail_response: str


# ── Query endpoint ────────────────────────────────────────────────────────────
@api.post("/query")
@limiter.limit("5/minute")           # max 5 requests per minute per IP
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
        "image_paths":          []
    })

    if result["guardrail_status"] == "blocked_input":
        last_message = result["guardrail_response"]
    elif result["guardrail_status"] == "blocked_output":
        last_message = result["guardrail_response"]
        save_session(session_key, result["conversation_history"], result.get("current_topic", ""))
    else:
        last_message = result["conversation_history"][-1].content
        save_session(session_key, result["conversation_history"], result.get("current_topic", ""))

    return QueryResponse(
        answer=last_message,
        citations=result["citations"],
        confidence_score=result["confidence_score"],
        guardrail_response=result["guardrail_response"]
    )