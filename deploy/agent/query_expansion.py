from config.settings import LLM_MODEL, client, QUERY_VARIATIONS_LIMIT

def query_expansion(state):
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": f"""Generate exactly {QUERY_VARIATIONS_LIMIT} alternative phrasings of the user query.
            Return only the {QUERY_VARIATIONS_LIMIT} variations, one per line, no numbering, no extra text."""},
            {"role": "user", "content": state["query"]}
        ]
    )
    raw = response.choices[0].message.content.strip()
    variations = [v.strip() for v in raw.split("\n") if v.strip()]
    return {"query_variations": variations}