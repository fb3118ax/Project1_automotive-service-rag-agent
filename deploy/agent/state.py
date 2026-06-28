from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage 
import operator

class Citation(TypedDict):
    page: int
    source: str

class AgentState(TypedDict):
    user_type: str
    query: str
    intent: str
    guardrail_status: str
    query_variations: list[str]
    guardrail_response: str
    retrieved_chunks: list[dict]
    confidence_score: float
    conversation_history: Annotated[list[BaseMessage], operator.add]
    citations: Annotated[list[Citation], operator.add]
    image_paths: Annotated[list[str], operator.add]
    image_captions: Annotated[list[str], operator.add]
    current_topic: str
    final_response: str       
    cache_hit: bool          