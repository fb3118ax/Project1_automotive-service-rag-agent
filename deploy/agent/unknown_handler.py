from langchain_core.messages import AIMessage, HumanMessage
from agent.state import AgentState

def unknown_handler(state):
    return {
        # FIX: return only the new message(s), not state["conversation_history"] + [...]
        # (operator.add reducer was causing history to duplicate every turn).
        # FIX: also record the user's query itself — previously only the AI
        # message was appended, so the user's turn was missing from history.
        "conversation_history": [
            HumanMessage(content=state["query"]),
            AIMessage(content="I couldn't find relevant information in the BMW service manual for your query. Please consult a certified BMW technician or visit your nearest service center.")
        ]
    }