
from better_profanity import profanity
profanity.load_censor_words() 
from config.settings import INJECTION_PATTERNS

def output_guardrail (state):
    response = state["conversation_history"][-1].content
    
    if any(pattern in response.lower() for pattern in INJECTION_PATTERNS):
        return {
            "guardrail_status": "blocked_output",
            "guardrail_response": "Invalid input detected.",
            "conversation_history": state["conversation_history"][:-1]
        }    
      
    elif profanity.contains_profanity(response):
        return {
                "guardrail_status": "blocked_output",
                "guardrail_response": "I'm unable to provide that response. Please consult a certified BMW technician.",
                "conversation_history": state["conversation_history"][:-1]  # remove last AIMessage
            }
    else:
        return {"guardrail_status": "pass", "guardrail_response": ""}