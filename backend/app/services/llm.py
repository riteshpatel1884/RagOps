"""Answer generation over retrieved context, via LangChain's ChatGroq wrapped
in a small LCEL chain (prompt | llm | output parser)."""
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from app.core.config import get_settings

settings = get_settings()

SYSTEM_PROMPT = """You are RAGOps' answer engine. Answer the user's question using ONLY the \
provided context chunks. Every claim must be traceable to a chunk.

Rules:
- If the context does not contain the answer, say so plainly — do not guess.
- After your answer, do not repeat the sources; the app renders them separately.
- Be concise and directly answer the question first, with brief supporting detail after.
"""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "Context:\n{context}\n\nQuestion: {question}"),
    ]
)

# Pipeline Builder's "LLM" dropdown pulls from this list — add/remove Groq
# model names here and they show up there automatically.
#
# NOTE: llama-3.3-70b-versatile / llama-3.1-8b-instant now show as
# "Enterprise" (contact-sales) on Groq's production models list — a normal
# API key gets a 404 on those. openai/gpt-oss-* are the current models with
# regular per-token pricing available on a standard Groq key. If Groq's
# lineup changes again, check https://console.groq.com/docs/models and swap
# the list below — nothing else in the app needs to change.
AVAILABLE_LLMS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
]


def build_context_block(chunks: list[Document]) -> str:
    parts = []
    for i, c in enumerate(chunks, start=1):
        # parent_child chunking retrieves on the small child chunk (precision)
        # but sends the larger parent chunk to the LLM as context (recall).
        text = c.metadata.get("parent_text") or c.page_content
        parts.append(f"[Source {i} — {c.metadata.get('filename')} p.{c.metadata.get('page_number')}]\n{text}")
    return "\n\n".join(parts)


def generate_answer(question: str, chunks: list[Document], model: str | None = None) -> str:
    if not settings.groq_api_key:
        return (
            "[No GROQ_API_KEY configured — set it in backend/.env to enable generation. "
            "Retrieval below is still real.]"
        )

    llm = ChatGroq(api_key=settings.groq_api_key, model=model or settings.groq_model, max_tokens=800)
    chain = PROMPT | llm | StrOutputParser()
    return chain.invoke({"context": build_context_block(chunks), "question": question})