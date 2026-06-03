from langchain_core.messages import AIMessage
from agent.state import AgentState

def unknown_handler(state):
    return {
        "conversation_history": state["conversation_history"] + [
            AIMessage(content="I couldn't find relevant information in the BMW service manual for your query. Please consult a certified BMW technician or visit your nearest service center.")
        ]
    }