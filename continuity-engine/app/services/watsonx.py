"""IBM watsonx / Granite LLM adapter.

Implements the LanguageModel protocol from app.reporting.explanations so the
ContinuityEngine can call it directly.

Usage:
    engine = ContinuityEngine(llm=WatsonxAdapter())

Falls back silently to rule-based text if credentials are missing or the
API call fails — the engine always produces a complete report either way.

To enable:
    1. pip install ibm-watsonx-ai
    2. Set environment variables:
       WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.schemas import Issue


_WATSONX_AVAILABLE = False
try:
    from ibm_watsonx_ai import APIClient, Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference
    _WATSONX_AVAILABLE = True
except ImportError:
    pass


class WatsonxAdapter:
    """Wraps IBM Granite via ibm-watsonx-ai SDK.

    Degrades to None (rule-based fallback) if the SDK or credentials
    are not available.
    """

    def __init__(
        self,
        model_id: str = "ibm/granite-3-8b-instruct",
        api_key: str | None = None,
        project_id: str | None = None,
        url: str | None = None,
    ) -> None:
        self._model_id = model_id
        self._api_key = api_key or os.getenv("WATSONX_API_KEY", "")
        self._project_id = project_id or os.getenv("WATSONX_PROJECT_ID", "")
        self._url = url or os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
        self._client: object | None = None
        self._available = _WATSONX_AVAILABLE and bool(self._api_key) and bool(self._project_id)

    def _get_client(self) -> object | None:
        if not self._available:
            return None
        if self._client is None:
            try:
                creds = Credentials(url=self._url, api_key=self._api_key)
                self._client = ModelInference(
                    model_id=self._model_id,
                    credentials=creds,
                    project_id=self._project_id,
                )
            except Exception:
                self._available = False
                return None
        return self._client

    def __call__(self, prompt: str) -> str:
        """Called by ExplanationWriter / SuggestionWriter."""
        client = self._get_client()
        if client is None:
            return ""
        try:
            response = client.generate_text(  # type: ignore[union-attr]
                prompt=prompt,
                params={"max_new_tokens": 200, "temperature": 0.2},
            )
            return str(response).strip()
        except Exception:
            return ""

    @property
    def is_available(self) -> bool:
        return self._available


def create_llm() -> WatsonxAdapter | None:
    """Create a WatsonxAdapter if credentials are present; return None otherwise."""
    adapter = WatsonxAdapter()
    return adapter if adapter.is_available else None


def create_semantic_matcher(adapter: WatsonxAdapter | None = None):
    """Return a SemanticMatcher callable backed by Granite embeddings.

    The matcher satisfies the app.ingestion.entity_matcher.SemanticMatcher
    protocol: it takes two name strings and returns a similarity score in [0, 1].

    If the adapter is unavailable (no credentials / SDK not installed), returns
    None so the engine falls back to its keyword synonym table — no change in
    behaviour from before.

    Usage inside get_or_create_engine:
        llm = create_llm()
        semantic_matcher = create_semantic_matcher(llm)
        engine = ContinuityEngine(..., semantic_matcher=semantic_matcher)
    """
    if adapter is None or not adapter.is_available:
        return None

    def _embed(text: str) -> list[float]:
        """Ask Granite to produce a 1-line embedding proxy via cosine-like prompt."""
        # ibm-watsonx-ai embeddings endpoint — uses a dedicated embedding model.
        # Falls back to 0.0 similarity on any failure so entity matching
        # simply degrades to the keyword path.
        try:
            from ibm_watsonx_ai import APIClient, Credentials
            from ibm_watsonx_ai.foundation_models import Embeddings
            from ibm_watsonx_ai.metanames import EmbedTextParamsMetaNames as EmbedParams
            import os, math

            creds = Credentials(
                url=os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com"),
                api_key=adapter._api_key,
            )
            client = Embeddings(
                model_id="ibm/slate-125m-english-rtrvr",
                credentials=creds,
                project_id=adapter._project_id,
                params={EmbedParams.TRUNCATE_INPUT_TOKENS: 32},
            )
            result = client.generate(inputs=[text])
            return result["results"][0]["embedding"]
        except Exception:
            return []

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

    def semantic_match(left: str, right: str) -> float:
        """Semantic similarity in [0, 1] between two entity name strings."""
        return _cosine(_embed(left), _embed(right))

    return semantic_match
