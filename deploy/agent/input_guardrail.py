from better_profanity import profanity
profanity.load_censor_words()  
from config.settings import INJECTION_PATTERNS

def input_guardrail(state):
    query = state["query"]
        
    
    if len(query.strip()) == 0:
        return {
            "guardrail_status": "blocked_input",
            "guardrail_response": "Please Enter a valid input"
        }
    
    elif len(query.strip()) > 500:
        return {
            "guardrail_status": "blocked_input",
            "guardrail_response": "Query is too long. Please keep it under 500 characters."
        }
    
    elif any(pattern in query.lower() for pattern in INJECTION_PATTERNS):
        return {
            "guardrail_status": "blocked_input",
            "guardrail_response": "Invalid input detected."
        }
    
    elif profanity.contains_profanity(query):
        return {
                "guardrail_status": "blocked_input",
                "guardrail_response": "Only to answer sevice related questions"
            }  
    else:
        return {"guardrail_status": "pass", "guardrail_response": ""}