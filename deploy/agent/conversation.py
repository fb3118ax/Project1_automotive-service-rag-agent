import tiktoken
from langchain_core.messages import AIMessage, HumanMessage
from config.settings import client, LLM_MODEL, CONFIDENCE_THRESHOLD, OWNER_MAX_WORDS, TOKEN_LIMIT
from agent.retrievers import _is_context_free_image_request, IMAGE_REQUEST_KEYWORDS

enc = tiktoken.encoding_for_model("gpt-4o")

def count_tokens(text):
    return len(enc.encode(text))

def _format_caption(caption: str) -> str:
    clean = caption.strip().strip('*')
    first_line = clean.split('\n')[0].strip()
    if len(first_line) > 200:
        sentences = first_line.split('. ')
        first_line = '. '.join(sentences[:2]).strip()
        if not first_line.endswith('.'):
            first_line += '.'
    return f"*{first_line}*"


def conversation(state):
    query_lower = state["query"].lower()
    explicit_image_request = any(word in query_lower for word in IMAGE_REQUEST_KEYWORDS)

    if _is_context_free_image_request(state["query"]) or explicit_image_request:
        image_paths = state.get("image_paths", [])
        image_captions = state.get("image_captions", [])
        if image_paths:
            parts = []
            for url, caption in zip(image_paths, image_captions):
                parts.append(f"![Image]({url})")
                if caption:
                    parts.append(_format_caption(caption))
            answer = "**Relevant Images:**\n" + "\n".join(parts)
        else:
            answer = "No relevant images found in the manual for this query."

        new_topic = state["query"] if not _is_context_free_image_request(state["query"]) else state.get("current_topic", "")
        return {
            "current_topic": new_topic,
            "conversation_history": state["conversation_history"] + [
                HumanMessage(content=state["query"]),
                AIMessage(content=answer)
            ]
        }

    if not state["retrieved_chunks"]:
        return {
            "current_topic": state.get("current_topic", ""),
            "conversation_history": state["conversation_history"] + [
                AIMessage(content="I couldn't find relevant information in your BMW manual for this query. Please consult a certified BMW technician.")
            ]
        }

    context = "\n\n".join([
        f"Page {chunk['metadata'].get('page_number', 'unknown')}:\n{chunk['content']}"
        for chunk in state["retrieved_chunks"]
    ])

    user_type     = state["user_type"]
    citation_text = "\n".join([f"- Page {c['page']}" for c in state["citations"]])

    if user_type == "owner":
        system_prompt = f"""You are a vehicle service manual assistant helping a car owner.
                        Use simple, non-technical language. Avoid jargon.
                        Always recommend visiting a certified service center for repairs.
                        Base your answer only on the provided manual context.
                        STRICTLY - Never mention that you cannot show images, display visuals, or provide diagrams. Do not reference images at all in your text response.
                        Reference these manual pages: {citation_text}
                        Keep the response concise and under {OWNER_MAX_WORDS} words."""
    else:
        system_prompt = f"""You are a vehicle service manual assistant helping a certified technician.
                        Use precise technical language. Include specifications, torque values, and part references where available.
                        Always cite the page number from the manual context in your response.
                        Base your answer only on the provided manual context.
                        STRICTLY - Never mention that you cannot show images, display visuals, or provide diagrams. Do not reference images at all in your text response.
                        Reference these manual pages: {citation_text}"""

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
        answer += "\n\n⚠️ Note: This answer is based on limited matches from the manual. Please verify with a certified technician."

    image_paths = state.get("image_paths", [])
    if image_paths:
        image_captions = state.get("image_captions", [])
        parts = []
        for url, caption in zip(image_paths, image_captions):
            parts.append(f"![Image]({url})")
            if caption:
                parts.append(_format_caption(caption))
        answer += "\n\n**Relevant Images:**\n" + "\n".join(parts)

    new_topic = state["query"]
    return {
        "current_topic": new_topic,
        "conversation_history": state["conversation_history"] + [
            HumanMessage(content=state["query"]),
            AIMessage(content=answer)
        ]
    }