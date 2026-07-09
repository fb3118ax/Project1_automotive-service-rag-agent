from config.settings import client, LLM_MODEL
from langchain_core.messages import HumanMessage


def classifier(state):
    VALID_ROUTES = ["text", "unknown"]

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
    max_tokens=10,
    temperature=0,
    messages=[
        {"role": "system", "content": """You are a routing assistant for a cars/vehicle service manual.
            Given a user query, decide which data source to search.

            Return only one of:

            text: any query related to vehicle/cars service, maintenance, specifications,
            warnings, procedures, error codes, dashboard indicators, safety systems,
            fluid types, component descriptions, operating instructions, diagnostics,
            or basic vehicle operation (entering, exiting, starting, driving the vehicle).
            Also includes the vehicle's built-in emergency call system (SOS button, automatic
            crash notification, emergency/breakdown assistance features) and how to use it —
            even when phrased generically, e.g. "emergency contact", "emergency number",
            "how do I call for help", "roadside assistance".
            Also includes requests to see images, diagrams, or visuals of any component or procedure.

            unknown: queries completely outside vehicle service manual scope.
            This includes:
            - Purchase intent: buying parts, accessories, pricing, where to buy, cost of parts
            - Dealer/retail queries: dealership locations, ordering parts online
            - General opinions: best car, car comparisons, recommendations
            - Non-automotive topics: jokes, weather, stocks, recipes, general knowledge
            - Harmful content: weapons, explosives, illegal activities
            - Vague queries with no automotive context

            When in doubt between text and unknown, prefer unknown."""},
        {"role": "user", "content": enriched_query}
    ]
)

    raw = response.choices[0].message.content
    print(f"[classifier] raw output for {state['query']!r}: {raw!r}")
    intent = response.choices[0].message.content.strip().lower()
    if "unknown" in intent:
        intent = "unknown"
    elif "text" in intent:
        intent = "text"
    else:
        intent = "unknown"
    
    return {"intent": intent}