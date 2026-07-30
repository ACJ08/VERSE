"""Provider-agnostic LangChain LLM adapter.

Implements the LanguageModel protocol from app.reporting.explanations so any
LangChain chat model can be dropped into the engine directly:

    from langchain_anthropic import ChatAnthropic
    engine = ContinuityEngine(llm=LangChainAdapter(ChatAnthropic(model=...)))

    from langchain_ibm import ChatWatsonx
    engine = ContinuityEngine(llm=LangChainAdapter(ChatWatsonx(model_id=...)))

The adapter never binds a provider itself — it wraps whatever LangChain
Runnable (chat model, prompt|model chain, ...) the caller hands it. Like
WatsonxAdapter it degrades silently: if no model is supplied or a call raises,
`__call__` returns "" and the engine keeps its rule-based text.
"""

from __future__ import annotations

import os
from typing import Any, Callable


class LangChainAdapter:
    """Wraps any LangChain Runnable (`.invoke(prompt) -> str | AIMessage`).

    Provider-agnostic by design: the model is injected, so the choice of
    Anthropic / watsonx / OpenAI / local lives with the caller, not here.
    """

    def __init__(
        self,
        model: Any | None = None,
        *,
        max_tokens: int = 200,
    ) -> None:
        self._model = model
        self._max_tokens = max_tokens

    def __call__(self, prompt: str) -> str:
        """Called by ExplanationWriter / SuggestionWriter / AssumptionEngine."""
        if self._model is None:
            return ""
        try:
            result = self._model.invoke(prompt)
        except Exception:
            return ""
        return _as_text(result)

    @property
    def is_available(self) -> bool:
        return self._model is not None


def _as_text(result: Any) -> str:
    """Coerce a LangChain result into a plain string.

    Chat models return a message object with `.content` (which may itself be a
    list of content blocks); plain LLMs and string Runnables return a str.
    """
    content = getattr(result, "content", result)
    if isinstance(content, list):
        # Multi-part content: keep the text blocks, drop tool/image parts.
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    return str(content).strip()


def create_llm(model: Any | None = None) -> LangChainAdapter | None:
    """Wrap `model` in a LangChainAdapter, or return None if there is nothing to wrap.

    Returning None (rather than an inert adapter) lets callers pass the result
    straight to `ContinuityEngine(llm=...)` and get the rule-based path when no
    model is configured — the same contract as watsonx.create_llm.
    """
    if model is None:
        return None
    adapter = LangChainAdapter(model)
    return adapter if adapter.is_available else None


def create_llm_from_env() -> LangChainAdapter | None:
    """Build an adapter from `VERSE_LLM_MODEL`, or return None if it is unset.

    `VERSE_LLM_MODEL` is a LangChain model spec such as "anthropic:claude-sonnet-5"
    or "openai:gpt-4o"; the provider comes from the string, so nothing here is
    provider-specific. Resolution uses LangChain's `init_chat_model`, which reads
    the provider's usual API-key env var (ANTHROPIC_API_KEY, ...).

    Returns None — the engine's rule-based path — when the var is unset, when
    langchain is not installed, or when the model fails to initialise.
    """
    spec = os.getenv("VERSE_LLM_MODEL", "").strip()
    if not spec:
        return None
    try:
        from langchain.chat_models import init_chat_model

        model = init_chat_model(spec)
    except Exception:
        return None
    return create_llm(model)


def create_semantic_matcher(embeddings: Any | None = None) -> Callable[[str, str], float] | None:
    """Return a SemanticMatcher backed by a LangChain Embeddings object.

    Satisfies app.ingestion.entity_matcher.SemanticMatcher: two name strings in,
    a similarity score in [0, 1] out. `embeddings` is any object exposing
    `embed_query(str) -> list[float]` (all LangChain Embeddings do).

    Returns None when no embeddings model is supplied, so entity matching falls
    back to the keyword synonym table with no change in behaviour.
    """
    if embeddings is None:
        return None

    def _embed(text: str) -> list[float]:
        try:
            return list(embeddings.embed_query(text))
        except Exception:
            return []

    def semantic_match(left: str, right: str) -> float:
        return _cosine(_embed(left), _embed(right))

    return semantic_match


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    import math

    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
