"""LLM-as-judge faithfulness scoring, via the same Groq models the app
already uses for generation.

Per the roadmap: "Don't treat an LLM judge as absolute truth." This module
returns None (not a fabricated number) whenever it can't get a real judge
call in — no GROQ_API_KEY, an empty answer/context, a malformed response, or
an API error — so callers fall back to a deterministic embedding-similarity
proxy instead of silently reporting a fake score.
"""
import re

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from app.core.config import get_settings

settings = get_settings()

JUDGE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a strict fact-checking judge. Given CONTEXT and an ANSWER, "
            "output ONLY a number between 0 and 1: the fraction of the answer's "
            "claims that are directly supported by the context. "
            "0 = fully unsupported or hallucinated. 1 = fully supported. "
            "Output nothing except the number — no words, no explanation.",
        ),
        ("human", "CONTEXT:\n{context}\n\nANSWER:\n{answer}\n\nScore:"),
    ]
)

_NUMBER_RE = re.compile(r"(\d*\.?\d+)")


def llm_judge_faithfulness(answer: str, context: str, model: str | None = None) -> float | None:
    """Returns a 0-1 faithfulness score, or None if a real judgment couldn't
    be obtained (caller should fall back to a deterministic proxy)."""
    if not settings.groq_api_key or not answer.strip() or not context.strip():
        return None
    try:
        llm = ChatGroq(
            api_key=settings.groq_api_key,
            model=model or settings.groq_model,
            max_tokens=10,
            temperature=0,
        )
        chain = JUDGE_PROMPT | llm
        response = chain.invoke({"context": context[:6000], "answer": answer[:2000]})
        match = _NUMBER_RE.search(response.content)
        if not match:
            return None
        score = float(match.group(1))
        return max(0.0, min(1.0, score))
    except Exception:
        return None