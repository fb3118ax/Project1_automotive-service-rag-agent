from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent.graph import app as agent_app
from agent.state import Citation

api = FastAPI()

api.add_middleware(
    CORSMiddleware,
    allow_origins=["https://project1-automotive-service-rag-age.vercel.app"],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

sessions: dict = {}

# Request — what client sends
class QueryRequest(BaseModel):
    query: str
    session_id: str
    user_type: str

# Response — what you send back
class QueryResponse(BaseModel):
    answer: str
    citations: list
    confidence_score: float
    guardrail_response : str

@api.post("/query")
async def query(request: QueryRequest):
    session_key = f"{request.session_id}_{request.user_type}"
    result = agent_app.invoke({
    "query": request.query,
    "user_type": request.user_type,
    "query_variations": [],
    "conversation_history": sessions.get(session_key, []),  # loaded from sessions dict
    "intent": "",
    "guardrail_status": "",    
    "guardrail_response": "", 
    "retrieved_chunks": [],
    "confidence_score": 0.0,
    "citations": [],
    "image_paths": []
    })
    if result["guardrail_status"] == "blocked_input":
        last_message = result["guardrail_response"]
    elif result["guardrail_status"] == "blocked_output":
        last_message = result["guardrail_response"]
        sessions[session_key] = result["conversation_history"] 
    else:
        last_message = result["conversation_history"][-1].content #That line reads the last message from the result. It does not save anything, This READS the last AIMessage content to return as the answer
        sessions[session_key] = result["conversation_history"] #This SAVES the full updated history back into sessions
    return QueryResponse(
    answer=last_message,
    citations=result["citations"],
    confidence_score=result["confidence_score"],
    guardrail_response=result["guardrail_response"] 
)