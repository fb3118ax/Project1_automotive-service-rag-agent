from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
import operator

class Citation(TypedDict):
    page: int
    section: str
    source: str

class AgentState(TypedDict):
    user_type: str
    query: str
    intent: str
    retrieved_chunks: Annotated[list[dict], operator.add]  # merge parallel writes
    confidence_score: float
    conversation_history: Annotated[list[BaseMessage], operator.add] 
    citations: Annotated[list[Citation], operator.add]  
    image_paths: Annotated[list[str], operator.add]