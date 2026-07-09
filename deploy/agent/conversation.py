import tiktoken
from langchain_core.messages import AIMessage, HumanMessage
from config.settings import client, LLM_MODEL, CONFIDENCE_THRESHOLD, OWNER_MAX_WORDS, TOKEN_LIMIT

enc = tiktoken.encoding_for_model("gpt-4o")

def count_tokens(text):
    return len(enc.encode(text))


NO_MATCH_MESSAGE = {
    "owner": "I couldn't find relevant information in your vehicle manual for this query. Please consult a certified technician.",
    "technician": "No relevant content was retrieved from the manual for this query. Verify against OEM documentation or workshop resources directly.",
}

LOW_CONFIDENCE_NOTE = {
    "owner": "\n\n⚠️ Note: This answer is based on limited matches from the manual. Please verify with a certified technician.",
    "technician": "\n\n⚠️ Note: This answer is based on limited matches from the manual. Cross-reference the cited pages directly before acting on it.",
}


def conversation(state):
    user_type = state["user_type"]

    if not state["retrieved_chunks"]:
        return {
            "current_topic": state.get("current_topic", ""),
            # FIX: return only the new message(s) — conversation_history uses
            # operator.add as its reducer, so LangGraph appends this to the
            # existing accumulated history automatically. Returning
            # state["conversation_history"] + [...] here caused the entire
            # prior history to be duplicated on every turn.
            "conversation_history": [
                AIMessage(content=NO_MATCH_MESSAGE.get(user_type, NO_MATCH_MESSAGE["owner"]))
            ]
        }

    context = "\n\n".join([
        f"Page {chunk['metadata'].get('page_number', 'unknown')}:\n{chunk['content']}"
        for chunk in state["retrieved_chunks"]
    ])

    citation_text = "\n".join([f"- Page {c['page']}" for c in state["citations"]])

    GROUNDING_RULE = """-If the manual context above does not contain the information needed to answer the question,
                    tell the user plainly that this specific information isn't covered in the vehicle's service manual.
                    Never say "the context you provided" or imply the user supplied the manual excerpts — the manual
                    content comes from the system, not the user. Stop there — do not offer a general approach,
                    a best guess, or steps drawn from outside the provided context, even if it seems helpful."""

    if user_type == "owner":
        system_prompt = f"""You are a vehicle service manual assistant helping a car owner.
                        -Use simple, non-technical language. Avoid jargon.
                        -Always recommend visiting a certified service center for repairs.
                        -Multiple chunks in the context may cover closely related topics (e.g. VIN location vs. production date location) — answer only the specific question asked 
                        and do not blend details from a different but similar topic.
                        -Base your answer only on the provided manual context.
                        {GROUNDING_RULE}
                        -If any Emergency or Safety information is present in the context, highlight it clearly in your response.
                        -Keep the response concise and under {OWNER_MAX_WORDS} words."""
    else:
        system_prompt = f"""You are a vehicle service manual assistant helping a certified technician.
                        -Use precise technical language. Include specifications, torque values, and part references where available.
                        -Always cite the page number from the manual context in your response.
                        -Multiple chunks in the context may cover closely related topics (e.g. VIN location vs. production date location) — answer only the specific question asked 
                        and do not blend details from a different but similar topic.
                        -Base your answer only on the provided manual context.
                        {GROUNDING_RULE}
                        -Reference these manual pages: {citation_text}"""

    history_text = " ".join([m.content for m in state["conversation_history"]])
    total_tokens = count_tokens(system_prompt + history_text + context + state["query"])
    history = state["conversation_history"]
    while total_tokens > TOKEN_LIMIT and len(history) > 0:
        history = history[2:]
        history_text = " ".join([m.content for m in history])
        total_tokens = count_tokens(system_prompt + history_text + context + state["query"])

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            *[{"role": "user" if isinstance(m, HumanMessage) else "assistant", "content": m.content}
              for m in history],
            {"role": "user", "content": f"{state['query']}\n\nContext:\n{context}"}
        ]
    )

    answer = response.choices[0].message.content.strip()

    if state["confidence_score"] < CONFIDENCE_THRESHOLD:
        answer += LOW_CONFIDENCE_NOTE.get(user_type, LOW_CONFIDENCE_NOTE["owner"])

    new_topic = state["query"]
    return {
        "current_topic": new_topic,
        # FIX: same as above — only the new turn's messages, not existing + new.
        "conversation_history": [
            HumanMessage(content=state["query"]),
            AIMessage(content=answer)
        ]
    }