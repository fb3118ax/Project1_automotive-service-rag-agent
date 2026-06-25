from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.classifier import classifier
from agent.retrievers import text_retriever, image_retriever
from agent.unknown_handler import unknown_handler
from agent.confidence_score import confidence_score
from agent.conversation import conversation
from agent.input_guardrail import input_guardrail
from agent.output_guardrail import output_guardrail
from agent.query_expansion import query_expansion


def route_after_input_guard(state):
    if state["guardrail_status"] == "pass":
        return ["classifier", "query_expansion"]
    return "blocked_input"


def route_intent(state):
    intent = state["intent"]
    if intent == "unknown":
        return "unknown_handler"
    else:
        return "text_retriever"


def route_after_output_guard(state):
    """Don't show images if output was blocked."""
    return END


graph = StateGraph(AgentState)
graph.add_node('input_guardrail',  input_guardrail)
graph.add_node('classifier',       classifier)
graph.add_node('query_expansion',  query_expansion)
graph.add_node('text_retriever',   text_retriever)
graph.add_node('image_retriever',  image_retriever)
graph.add_node('unknown_handler',  unknown_handler)
graph.add_node('confidence',       confidence_score)
graph.add_node('conversation',     conversation)
graph.add_node('output_guardrail', output_guardrail)

graph.set_entry_point('input_guardrail')

graph.add_conditional_edges(
    "input_guardrail",
    route_after_input_guard,
    {
        "blocked_input":   END,
        "classifier":      "classifier",
        "query_expansion": "query_expansion"
    }
)

graph.add_conditional_edges(
    "classifier",
    route_intent,
    {
        "text_retriever":  "text_retriever",
        "unknown_handler": "unknown_handler"
    }
)

# image_retriever runs in parallel with text_retriever via query_expansion
graph.add_edge('query_expansion',  'text_retriever')
graph.add_edge('query_expansion',  'image_retriever')
graph.add_edge('text_retriever',   'confidence')
graph.add_edge('image_retriever',  'confidence')
graph.add_edge('unknown_handler',  END)
graph.add_edge('confidence',       'conversation')
graph.add_edge('conversation',     'output_guardrail')
graph.add_edge('output_guardrail', END)

app = graph.compile()