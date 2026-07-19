from config.settings import LLM_MODEL, client, QUERY_VARIATIONS_LIMIT


def query_expansion(state):
    current_topic = state.get("current_topic", "")
    query = state["query"]

    # Fold in the prior topic so short follow-ups ("how can I do that?",
    # "why?", "where is it?") expand into something retrieval can actually
    # match, instead of being searched literally on their own.
    if current_topic:
        seed = f"Previous topic: {current_topic}\nFollow-up question: {query}"
    else:
        seed = query

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": f"""# Role
                        You are a technical query expansion assistant for a service manual.

                        # Task
                        Generate exactly {QUERY_VARIATIONS_LIMIT} alternative phrasings of the user query, resolving any vague pronouns using the previous topic if given. 

                        # Constraints
                        - Strict Domain: Stay entirely within the automotive manual domain.
                        - Plain Technical Language: Do not use marketing jargon like "luxury vehicle interface". Use highly literal, mechanical, and physical component terms that would appear in a technical manual index (e.g., "switches", "controls", "layout").
                        - Output Format: Return only the {QUERY_VARIATIONS_LIMIT} variations, one per line, no numbering, no extra text.

                        # Examples
                        Input Query: "steering wheel buttons"
                        multifunction steering wheel switches
                        steering wheel control buttons
                        steering wheel layout"""
            },
            {"role": "user", "content": seed},
        
        ],
        temperature=0
    )
    raw = response.choices[0].message.content.strip()
    variations = [v.strip() for v in raw.split("\n") if v.strip()]
    print(
        f"[query_expansion] original: {query!r} -> variants: {variations}"
    )  # temp diagnostic
    return {"query_variations": variations}
