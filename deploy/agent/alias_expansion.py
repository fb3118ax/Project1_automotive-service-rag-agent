# alias_expansion.py
from config.settings import LLM_MODEL, client

_cache = {}

def expand_aliases(query: str) -> str:
    key = query.strip().lower()
    if key in _cache:
        return _cache[key]

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": (
                """You are an alias expansion assistant for a cars/vehicle service manual.
                Given a user query, expand any aliases, abbreviations, or shorthand into their full forms.
                For example, "ABS" should be expanded to "Anti-lock Braking System", "ECU" should be expanded to 'Engine Control Unit' and "SOS" to 'Emergency Call System'.
                append the automotive meaning to the query. Do not use general/dictionary definitions. If no acronym is present, return the query unchanged. Return only the query text.
                """
            )},
            {"role": "user", "content": query}
        ]
    )
    expanded = response.choices[0].message.content.strip()
    _cache[key] = expanded
    return expanded


def alias_expansion(state):
    expanded = expand_aliases(state["query"])
    print(f"[alias_expansion] {state['query']!r} -> {expanded!r}")  # temp diagnostic
    return {"query": expanded}