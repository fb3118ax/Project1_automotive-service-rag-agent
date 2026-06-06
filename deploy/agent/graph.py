from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.classifier import classifier
from agent.retrievers import text_retriever
from agent.unknown_handler import unknown_handler
from agent.confidence_score import confidence_score
from agent.conversation import conversation
from agent.input_guardrail import input_guardrail
from agent.output_guardrail import output_guardrail

def route_after_input_guard(state):
    if state["guardrail_status"] == "pass":
        return "classifier"
    return "blocked_input"

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
graph.add_node('input_guardrail', input_guardrail)
graph.add_node('classifier', classifier)
graph.add_node('text_retriever', text_retriever)   
graph.add_node('unknown_handler', unknown_handler)   
graph.add_node("confidence", confidence_score)
graph.add_node("conversation", conversation)
graph.add_node('output_guardrail', output_guardrail)

graph.set_entry_point('input_guardrail')
graph.add_conditional_edges(
    "input_guardrail",      
    route_after_input_guard,     
    {
        "blocked_input": END,
        "pass": "classifier"
    }
)
graph.add_conditional_edges(
    "classifier",      
    route_intent,      
    {
        "text_retriever": "text_retriever",        
        "unknown_handler" : "unknown_handler"
    }
)

graph.add_edge('text_retriever', 'confidence')   
graph.add_edge('unknown_handler', END)
graph.add_edge('confidence', 'conversation') 
graph.add_edge('conversation', 'output_guardrail')
graph.add_edge('output_guardrail', END)

app = graph.compile()