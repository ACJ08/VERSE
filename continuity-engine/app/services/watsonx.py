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
