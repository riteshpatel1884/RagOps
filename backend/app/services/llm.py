"""Answer generation over retrieved context, using the Anthropic API."""
import anthropic

from app.core.config import get_settings

settings = get_settings()

SYSTEM_PROMPT = """You are RAGOps' answer engine. Answer the user's question using ONLY the \
provided context chunks. Every claim must be traceable to a chunk.

Rules:
- If the context does not contain the answer, say so plainly — do not guess.
- After your answer, do not repeat the sources; the app renders them separately.
- Be concise and directly answer the question first, with brief supporting detail after.
"""


def build_context_block(chunks: list[dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, start=1):
        # parent_child chunking retrieves on the small child chunk (precision)
        # but sends the larger parent chunk to the LLM as context (recall).
        text = c.get("parent_text") or c["text"]
        parts.append(f"[Source {i} — {c['filename']} p.{c['page_number']}]\n{text}")
    return "\n\n".join(parts)


AVAILABLE_LLMS = ["claude-sonnet-4-6", "claude-haiku-4-5-20251001", "claude-opus-5"]


def generate_answer(question: str, chunks: list[dict], model: str | None = None) -> str:
    if not settings.anthropic_api_key:
        return (
            "[No ANTHROPIC_API_KEY configured — set it in backend/.env to enable generation. "
            "Retrieval below is still real.]"
        )
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    context = build_context_block(chunks)
    message = client.messages.create(
        model=model or settings.anthropic_model,
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}",
            }
        ],
    )
    return "".join(block.text for block in message.content if block.type == "text")
