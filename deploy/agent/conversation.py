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

UNGROUNDED_TAG = "[UNGROUNDED]"
UNSUPPORTED_RESPONSE_PATTERNS = (
    "isn't covered",
    "is not covered",
    "not covered",
    "not available",
    "doesn't mention",
    "does not mention",
    "couldn't find relevant information",
    "no relevant content",
)


def conversation(state):
    user_type = state["user_type"]

    if not state["retrieved_chunks"]:
        return {
            "current_topic": state.get("current_topic", ""),
            "grounded": False,
            "conversation_history": [
                AIMessage(content=NO_MATCH_MESSAGE.get(user_type, NO_MATCH_MESSAGE["owner"]))
            ]
        }

    context = "\n\n".join([
        f"Page {chunk['metadata'].get('page_number', 'unknown')}:\n{chunk['content']}"
        for chunk in state["retrieved_chunks"]
    ])

    citation_text = "\n".join([f"- Page {c['page']}" for c in state["citations"]])

    GROUNDING_RULE = f"""IMPORTANT Rules:
                    1. If the manual context clearly contains the answer, give a concise answer based only on that context.
                    2. If the context is only partially related or does not explicitly state the answer, do not invent facts. Instead:
                        - give a short, cautious response,
                        - say that the manual context is limited or does not clearly provide the answer,
                        - avoid offering general advice or assumptions.
                    3. If confidence is low, don't fabricate a vague answer — say clearly the manual doesn't cover this.
                    4. Do not mention the user supplied the context. Do not say "the context you provided". Speak as if the information comes from the vehicle manual.
                    5. Keep the reply short, helpful, and conservative.
                    6. Never provide outside knowledge or guesswork."""
    
    if user_type == "owner":
        system_prompt = f"""# Role -
                            You are a manual assistant for car owners. Use simple, non-technical language. Avoid jargon.

                            # Rules
                            1. **Synthesis Strategy**: Combine chunks if they provide complementary details on the *same* topic. Do *not* blend details if chunks describe different specific items/procedures (e.g., VIN location vs. production date).
                            2. **Safety**: Always advise visiting a certified service center for repairs. Boldly highlight any Emergency/Safety text.
                            3. **Constraints**: Base answers STRICTLY on the provided manual context. Keep responses concise and under {OWNER_MAX_WORDS} words.
                            {GROUNDING_RULE}
                            4. Examples are illustrative only — do not use their facts/pages in answers.

                            # Examples
                            - *Query*: "What do wheel buttons do?" | *Context*: [C1: Left buttons control audio] [C2: Right buttons control cruise]
                            *Output*: The left buttons control your audio volume, and the right buttons manage your cruise control. For repairs, visit a certified service center.
                            - *Query*: "Where is my VIN?" | *Context*: [C1: VIN is on the windshield] [C2: Production date is on the door]
                            *Output*: Your VIN is located on the lower corner of the driver's side windshield.
                            - Note : Examples are illustrative only — do not use their facts/pages in answers."""
    else:
        system_prompt = f"""# Role -
                            You are a manual assistant for certified technicians. Use precise technical language (specs, torque, parts).

                            # Rules
                            1. **Synthesis Strategy**: Combine chunks if they provide complementary technical steps/specs for the *same* procedure. Do *not* blend details if chunks describe distinct components or different model variants (e.g., VIN vs. production label).
                            2. **Citations**: Always cite manual page numbers inline. Reference pages: {citation_text}
                            3. **Constraints**: Base answers STRICTLY on the provided manual context.
                            {GROUNDING_RULE}
                            4. Examples are illustrative only — do not use their facts/pages in answers.

                            # Examples
                            - *Query*: "Install wheel controls." | *Context*: [p.42: Torque screws to 5 Nm] [p.89: Connect 12-pin harness first]
                            *Output*: Connect the 12-pin wiring harness before seating the unit (p. 89), then tighten the base screws to 5 Nm (p. 42).
                            - *Query*: "Where is VIN plate?" | *Context*: [p.12: VIN is on A-pillar] [p.15: Production label is on B-pillar]
                            *Output*: The VIN plate is riveted to the driver-side A-pillar structure (p. 12).
                            - Note : Examples are illustrative only — do not use their facts/pages in answers."""
        
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

    lower_answer = answer.lower()
    if answer.startswith(UNGROUNDED_TAG):
        answer = answer[len(UNGROUNDED_TAG):].strip()
        grounded = False
    elif any(pattern in lower_answer for pattern in UNSUPPORTED_RESPONSE_PATTERNS):
        grounded = False
    elif state["confidence_score"] < CONFIDENCE_THRESHOLD:
        answer = (
            f"{answer.strip()}\n\n"
            f"{LOW_CONFIDENCE_NOTE.get(user_type, LOW_CONFIDENCE_NOTE['owner'])}"
        )
        grounded = False
    else:
        grounded = True

    new_topic = state["query"]
    return {
        "current_topic": new_topic,
        "grounded": grounded,
        "conversation_history": [
            HumanMessage(content=state["query"]),
            AIMessage(content=answer, additional_kwargs={
                "citations": state["citations"] if grounded else [],
                "confidence_score": state["confidence_score"] if grounded else 0.0,
            })
        ]
    }