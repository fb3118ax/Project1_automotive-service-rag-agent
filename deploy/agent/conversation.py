import tiktoken
from langchain_core.messages import AIMessage, HumanMessage
from config.settings import client, LLM_MODEL, CONFIDENCE_THRESHOLD, OWNER_MAX_WORDS, TOKEN_LIMIT

enc = tiktoken.encoding_for_model("gpt-4o")

def count_tokens(text):
    return len(enc.encode(text))


def conversation(state):
    if not state["retrieved_chunks"]:
        return {
            "conversation_history": state["conversation_history"] + [
                AIMessage(content="I couldn't find relevant information in your BMW manual for this query. Please consult a certified BMW technician.")
            ]
        }

    context = "\n\n".join([
        f"Page {chunk['metadata'].get('page_number', 'unknown')}:\n{chunk['content']}"
        for chunk in state["retrieved_chunks"]
    ])

    user_type    = state["user_type"]
    citation_text = "\n".join([f"- Page {c['page']}" for c in state["citations"]])

    if user_type == "owner":
        system_prompt = f"""You are a BMW service manual assistant helping a car owner.
                        Use simple, non-technical language. Avoid jargon.
                        Always recommend visiting a certified BMW service center for repairs.
                        Base your answer only on the provided manual context.
                        Reference these manual pages: {citation_text}
                        Keep the response concise and under {OWNER_MAX_WORDS} words."""
    else:
        system_prompt = f"""You are a BMW service manual assistant helping a certified technician.
                        Use precise technical language. Include specifications, torque values, and part references where available.
                        Always cite the page number from the manual context in your response.
                        Base your answer only on the provided manual context.
                        Reference these manual pages: {citation_text}"""

    # Token limit check before sending to LLM
    history_text = " ".join([m.content for m in state["conversation_history"]])
    total_tokens = count_tokens(system_prompt + history_text + context + state["query"])
    history = state["conversation_history"]
    while total_tokens > TOKEN_LIMIT and len(history) > 0:
        history = history[2:]  # remove oldest human+assistant pair
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
        answer += "\n\n⚠️ Note: This answer is based on limited matches from the manual. Please verify with a certified BMW technician."

    # Append relevant image URLs if available
    image_paths = state.get("image_paths", [])
    if image_paths:
        image_links = "\n".join([f"![Image]({url})" for url in image_paths[:3]])  # max 3 images
        answer += f"\n\n**Relevant Images:**\n{image_links}"

    return {
        "conversation_history": state["conversation_history"] + [
            HumanMessage(content=state["query"]),
            AIMessage(content=answer)
        ]
    }