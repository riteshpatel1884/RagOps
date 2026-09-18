"""
Generation layer: turns (question + retrieved context) into an answer.

Two implementations, same pattern as embedder.py:

1. ExtractiveGenerator (default here) — no LLM call at all. Picks the
   sentence(s) from the retrieved context with the highest lexical overlap
   with the question. Used as the default because this sandbox has no LLM
   API credentials / network access to call one.

2. LangChainLLMGenerator — wraps any LangChain chat model (ChatOpenAI,
   ChatAnthropic, ChatGroq, ChatOllama, etc.) behind the same interface.
   This is the real production generator — swap it in with
   `get_generator("openai")`, `get_generator("anthropic")`, or
   `get_generator("groq")` once you have the matching API key set.
   Nothing else in the pipeline changes.
"""
import re
import os
from abc import ABC, abstractmethod
from typing import List
from langchain_core.prompts import ChatPromptTemplate

STOPWORDS = {
    "the", "a", "an", "is", "are", "do", "does", "of", "to", "in", "for", "on", "and", "or",
    "what", "how", "can", "many", "much", "i", "my", "will", "be", "am", "get", "gets",
}

RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a precise assistant that answers questions using ONLY the "
            "provided context. If the context doesn't contain the answer, say so. "
            "Do not add information that isn't in the context.",
        ),
        ("human", "Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"),
    ]
)


class BaseGenerator(ABC):
    name: str = "base"

    @abstractmethod
    def generate(self, question: str, context: List[str]) -> str:
        """Return a generated answer string given the question and retrieved context chunks."""


class ExtractiveGenerator(BaseGenerator):
    """
    Offline generator: no LLM call. Splits context into sentences and returns
    the ones with the most word overlap with the question. This is a crude
    but legitimate "extractive QA" baseline — many early QA systems worked
    exactly this way before generative LLMs.
    """

    name = "extractive (offline)"

    def _keywords(self, text: str) -> set:
        words = re.findall(r"[a-z0-9]+", text.lower())
        return {w for w in words if w not in STOPWORDS and len(w) > 2}

    def generate(self, question: str, context: List[str]) -> str:
        q_words = self._keywords(question)
        full_text = " ".join(context)
        sentences = re.split(r"(?<=[.!?])\s+", full_text)

        scored = []
        for sent in sentences:
            sent_words = self._keywords(sent)
            overlap = len(q_words & sent_words)
            if overlap > 0:
                scored.append((overlap, sent.strip()))

        if not scored:
            return "The retrieved context does not appear to contain an answer to this question."

        scored.sort(key=lambda x: x[0], reverse=True)
        top_sentences = [s for _, s in scored[:2]]
        return " ".join(top_sentences)


class LangChainLLMGenerator(BaseGenerator):
    """Wraps any LangChain chat model behind the BaseGenerator interface."""

    name = "langchain-llm"

    def __init__(self, chat_model):
        self.chat_model = chat_model
        self.chain = RAG_PROMPT | self.chat_model

    def generate(self, question: str, context: List[str]) -> str:
        response = self.chain.invoke({"question": question, "context": "\n\n".join(context)})
        return response.content


def get_generator(name: str = "extractive", **kwargs) -> BaseGenerator:
    """Factory so pipeline configs can select a generator by name."""
    if name in ("extractive", "offline", "default"):
        return ExtractiveGenerator()

    if name == "openai":
        from langchain_openai import ChatOpenAI  # requires OPENAI_API_KEY + network
        kwargs.setdefault("model", "gpt-4o-mini")
        return LangChainLLMGenerator(ChatOpenAI(**kwargs))

    if name == "anthropic":
        from langchain_anthropic import ChatAnthropic  # requires ANTHROPIC_API_KEY + network
        kwargs.setdefault("model", "claude-sonnet-4-5")
        return LangChainLLMGenerator(ChatAnthropic(**kwargs))

    if name == "groq":
        from langchain_groq import ChatGroq  # requires GROQ_API_KEY + network
        kwargs.setdefault("model", os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"))
        return LangChainLLMGenerator(ChatGroq(**kwargs))

    raise ValueError(f"Unknown generator: {name}")