
from better_profanity import profanity
profanity.load_censor_words() 
from config.settings import INJECTION_PATTERNS

def output_guardrail(state):
    response = state["conversation_history"][-1].content

    if any(pattern in response.lower() for pattern in INJECTION_PATTERNS):
        return {
            "guardrail_status": "blocked_output",
            "guardrail_response": "Invalid input detected.",
            "current_topic": state.get("current_topic", ""),
            "conversation_history": state["conversation_history"][:-1]
        }

    elif "![Image](" in response:
        return {
            "guardrail_status": "pass",
            "guardrail_response": "",
            "current_topic": state.get("current_topic", "")
        }

    elif profanity.contains_profanity(response):
        return {
            "guardrail_status": "blocked_output",
            "guardrail_response": "I'm unable to provide that response. Please consult a certified BMW technician.",
            "current_topic": state.get("current_topic", ""),
            "conversation_history": state["conversation_history"][:-1]
        }
    else:
        return {
            "guardrail_status": "pass",
            "guardrail_response": "",
            "current_topic": state.get("current_topic", "")
        }