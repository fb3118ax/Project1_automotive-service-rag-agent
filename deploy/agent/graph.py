from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.classifier import classifier
from agent.retrievers import text_retriever
from agent.unknown_handler import unknown_handler
from agent.confidence_score import confidence_score
from agent.conversation import conversation
# from agent.graph import app as agent_app

def route_intent(state):
    intent = state["intent"]
    if intent == "both":
        return "text_retriever"  # no real tables in this manual
    elif intent == "table":
        return "text_retriever"  # no real tables in this manual
    elif intent == "unknown":
        return "unknown_handler"
    else:
        return "text_retriever"
    

graph = StateGraph(AgentState)
graph.add_node('classifier', classifier)
graph.add_node('text_retriever', text_retriever)   
# graph.add_node('table_retriever', table_retriever) # removed since no table in manual, keeping it if next manual has the table in it
graph.add_node('unknown_handler', unknown_handler)   
graph.add_node("confidence", confidence_score)
graph.add_node("conversation", conversation)

graph.set_entry_point('classifier')
graph.add_conditional_edges(
    "classifier",      # after this node
    route_intent,      # call this function
    {
        "text_retriever": "text_retriever",
        # "table_retriever": "table_retriever",
        "unknown_handler" : "unknown_handler"
    }
)

graph.add_edge('text_retriever', 'confidence')   
# graph.add_edge('table_retriever', 'confidence') # removed since no table in manual, keeping it if next manual has the table in it 
graph.add_edge('unknown_handler', END)
graph.add_edge('confidence', 'conversation') 
graph.add_edge('conversation', END) 


app = graph.compile()