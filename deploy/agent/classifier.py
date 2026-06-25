from agent.state import AgentState
from config.settings import client, LLM_MODEL
from langchain_core.messages import HumanMessage


def classifier(state):
    VALID_ROUTES = ["text", "both", "unknown"]

    history = state["conversation_history"]
    if history:
        recent = history[-2:] if len(history) >= 2 else history
        context = "\n".join([
            f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
            for m in recent
        ])
        enriched_query = f"Previous exchange:\n{context}\n\nCurrent query: {state['query']}"
    else:
        enriched_query = state["query"]

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": """You are a routing assistant for a BMW service manual.
                    Given a user query, decide which data source to search.

                    Return only one of:

                    text: descriptive information, procedures, explanations, warnings,
                    fluid types and specifications (e.g. which oil to use),
                    component descriptions, operating instructions, warning lights,
                    error codes, dashboard indicators, safety systems

                    both: multiple symptoms, diagnostic queries, anything where
                    the answer needs both an explanation AND a spec value,
                    strange noises, car not starting, complex issues

                    unknown: queries completely outside vehicle service manual scope —
                    stock prices, financial information, jokes, riddles, general knowledge,
                    dealer locations, purchase advice, non-automotive topics,
                    anything unrelated to vehicle operation, maintenance, or repair.
                    Vague queries like "something is wrong" with no automotive context = unknown."""},
            {"role": "user", "content": enriched_query}
        ]
    )

    intent = response.choices[0].message.content.strip().lower()
    if intent not in VALID_ROUTES:
        intent = "unknown"
    return {"intent": intent}