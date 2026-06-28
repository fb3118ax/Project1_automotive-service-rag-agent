from better_profanity import profanity
profanity.load_censor_words()
from config.settings import INJECTION_PATTERNS
from agent.semantic_cache import write_cache

def output_guardrail(state):
    response = state["conversation_history"][-1].content

    if any(pattern in response.lower() for pattern in INJECTION_PATTERNS):
        return {
            "guardrail_status":   "blocked_output",
            "guardrail_response": "Invalid input detected.",
            "current_topic":      state.get("current_topic", ""),
            "final_response":     "",
            "conversation_history": state["conversation_history"][:-1],
        }

    elif "![Image](" in response:
        if not state.get("cache_hit"):
            write_cache({**state, "final_response": response})
        return {
            "guardrail_status":   "pass",
            "guardrail_response": "",
            "current_topic":      state.get("current_topic", ""),
            "final_response":     response,
        }

    elif profanity.contains_profanity(response):
        return {
            "guardrail_status":   "blocked_output",
            "guardrail_response": "I'm unable to provide that response. Please consult a certified technician.",
            "current_topic":      state.get("current_topic", ""),
            "final_response":     "",
            "conversation_history": state["conversation_history"][:-1],
        }

    else:
        if not state.get("cache_hit"):
            write_cache({**state, "final_response": response})
        return {
            "guardrail_status":   "pass",
            "guardrail_response": "",
            "current_topic":      state.get("current_topic", ""),
            "final_response":     response,
        }