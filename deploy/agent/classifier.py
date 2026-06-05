from agent.state import AgentState
from config.settings import client, LLM_MODEL
from langchain_core.messages import HumanMessage # added because providing history (enriched_query) to the agent with current one


def classifier (state):
    VALID_ROUTES = ["text", "table", "both", "unknown"]
    # added enriched_history for follow-up questions
    history = state["conversation_history"]
    if history:
    # get last 2 messages
        recent = history[-2:] if len(history) >= 2 else history
        context = "\n".join([
            f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
            for m in recent
        ])
        enriched_query = f"Previous exchange:\n{context}\n\nCurrent query: {state['query']}"
    else:
        enriched_query = state["query"]

    response = client.chat.completions.create(
                model= LLM_MODEL,
                messages=[
                {"role": "system", "content": """You are a routing assistant for a BMW service manual.
                        Given a user query, decide which data source to search.

                        Return only one of-
                        text: descriptive information, procedures, explanations, warnings, 
                        fluid types and specifications (e.g. which oil to use), 
                        component descriptions, operating instructions
                 
                        table: numerical specs, exact measurements, torque values (e.g. 25 Nm), 
                        service intervals (e.g. every 10,000 miles), scheduled maintenance dates, 
                        fault/error codes, fluid capacities in exact quantities
  
                        both: multiple symptoms, diagnostic queries, anything where 
                        the answer needs both an explanation AND a spec value, 
                        strange noises, car not starting, complex issues
                 
                        unknown: ONLY use this for queries that are completely 
                        outside vehicle service manual scope — prices, dealer 
                        locations, purchase advice, non-automotive topics.
                        Any query about vehicle symptoms, warnings, maintenance, 
                        repairs, or parts belongs to text/table/both."""},
                {"role": "user", "content": enriched_query}
                ])
    
    intent = response.choices[0].message.content.strip().lower()
    if intent not in VALID_ROUTES:
        intent = "unknown"
    return {"intent": intent}
                    