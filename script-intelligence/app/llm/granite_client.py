"""
VERSE LLM - Local IBM Granite 4.1 & Ollama Client Integration Layer.
"""

from __future__ import annotations

import json
import os
import re
from threading import Lock
from typing import Any, Optional, List

from openai import OpenAI, OpenAIError, APIConnectionError, APITimeoutError

from app.core.config import settings
from app.core.errors import InferenceError, ValidationError
from app.core.logging import get_logger, timed_execution
from app.llm.retry import retry_with_backoff
from app.prompts.templates import CONTINUITY_SYSTEM_PROMPT, build_user_prompt
from app.parsers.scene_splitter import parse_scene_metadata
from app.schemas.continuity import (
    Character,
    ContinuityNote,
    Lighting,
    Prop,
    SceneContinuity,
    SceneMetadata,
)

logger = get_logger(__name__)


class GraniteClient:
    """
    Client managing communication with local IBM Granite / Ollama inference server.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self._base_url: str = (base_url or settings.GRANITE_BASE_URL).rstrip("/")
        self._model: str = model or settings.GRANITE_MODEL
        self._api_key: str = api_key or settings.GRANITE_API_KEY
        self._timeout: float = timeout or settings.LLM_TIMEOUT_SECONDS

        self._client = OpenAI(
            base_url=self._base_url,
            api_key=self._api_key,
            timeout=self._timeout,
        )

    def _call_generation_api_raw(self, prompt: str) -> str:
        """
        Send chat completion request to OpenAI-compatible server.
        """
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": CONTINUITY_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=1024,
            )
            content = response.choices[0].message.content
            if not content or not content.strip():
                raise InferenceError("Granite inference server returned empty completion content.")
            return content
        except APIConnectionError as exc:
            logger.error("Connection failed to Granite server at %s: %s", self._base_url, exc)
            raise InferenceError(
                f"Unable to connect to Granite inference server at {self._base_url}: {exc}",
                status_code=503,
            ) from exc
        except APITimeoutError as exc:
            logger.error("Granite request timed out after %.1fs at %s: %s", self._timeout, self._base_url, exc)
            raise InferenceError(
                f"Granite inference request timed out after {self._timeout} seconds: {exc}",
                status_code=504,
            ) from exc
        except OpenAIError as exc:
            logger.error("Granite API request error: %s", exc)
            raise InferenceError(
                f"Local Granite inference request failed: {exc}",
                status_code=503,
            ) from exc

    def _call_generation_api(self, prompt: str) -> str:
        """
        Call generation API with automated backoff retry logic for transient errors.
        """
        retry_fn = retry_with_backoff(
            retries=settings.LLM_MAX_RETRIES,
            backoff_factor=1.0,
            exceptions=(InferenceError, APIConnectionError, APITimeoutError)
        )(self._call_generation_api_raw)
        return retry_fn(prompt)

    @staticmethod
    def _extract_json_block(text: str) -> dict[str, Any]:
        """
        Extract and parse a JSON object from LLM response text, performing fence stripping and repair.
        """
        # Strip markdown code fences
        stripped = re.sub(r"```(?:json)?", "", text).strip().strip("`")

        # Find outermost brackets
        match = re.search(r"\{.*\}", stripped, re.DOTALL)
        if not match:
            raise ValidationError(f"No JSON object found in model output: {text[:200]!r}")

        raw_json = match.group(0)
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError:
            # Simple JSON repair attempt: clean trailing commas before closing braces/brackets
            repaired = re.sub(r",\s*([\}\]])", r"\1", raw_json)
            try:
                return json.loads(repaired)
            except json.JSONDecodeError as exc:
                raise ValidationError(
                    f"Model returned malformed JSON: {exc} | raw: {raw_json[:200]!r}"
                ) from exc

    def analyse_scene(
        self,
        scene_text: str,
        scene_id: str = "SCENE_001",
    ) -> SceneContinuity:
        """
        Extract structured continuity data for one screenplay scene using Granite / Ollama.
        """
        user_prompt = build_user_prompt(scene_text)

        logger.info("Sending scene '%s' to local Granite (%s) for analysis.", scene_id, self._model)
        
        with timed_execution(f"Granite analysis for scene '{scene_id}'", logger):
            raw_output: str = self._call_generation_api(user_prompt)

        parsed: dict[str, Any] = self._extract_json_block(raw_output)

        # Parse scene metadata
        metadata = parse_scene_metadata(scene_text=scene_text, scene_id=scene_id)

        # Validate sub-models safely
        characters: list[Character] = []
        for c in parsed.get("characters", []):
            try:
                characters.append(Character.model_validate(c))
            except Exception as e:
                logger.warning("Skipping invalid character entry in scene '%s': %s", scene_id, e)

        props: list[Prop] = []
        for p in parsed.get("props", []):
            try:
                props.append(Prop.model_validate(p))
            except Exception as e:
                logger.warning("Skipping invalid prop entry in scene '%s': %s", scene_id, e)

        lighting_data = parsed.get("lighting")
        lighting: Optional[Lighting] = None
        if lighting_data:
            try:
                lighting = Lighting.model_validate(lighting_data)
            except Exception as e:
                logger.warning("Skipping invalid lighting data in scene '%s': %s", scene_id, e)

        continuity_notes: list[ContinuityNote] = []
        for n in parsed.get("continuity_notes", []):
            try:
                continuity_notes.append(ContinuityNote.model_validate(n))
            except Exception as e:
                logger.warning("Skipping invalid continuity note in scene '%s': %s", scene_id, e)

        # Calculate heuristic extraction confidence score
        confidence = 1.0
        if not characters and not props and not continuity_notes:
            confidence = 0.7  # Partial or simple scene

        return SceneContinuity(
            metadata=metadata,
            characters=characters,
            props=props,
            lighting=lighting,
            continuity_notes=continuity_notes,
            confidence_score=confidence,
            raw_scene_text=scene_text,
        )


# Lazy singleton instance
_client_instance: Optional[GraniteClient] = None
_client_lock = Lock()


def get_client() -> GraniteClient:
    """Return the module-level GraniteClient singleton instance."""
    global _client_instance
    with _client_lock:
        if _client_instance is None:
            _client_instance = GraniteClient()
    return _client_instance


def analyse_scene(scene_text: str, scene_id: str = "SCENE_001") -> SceneContinuity:
    """Convenience module-level function for single scene analysis."""
    return get_client().analyse_scene(scene_text=scene_text, scene_id=scene_id)


def is_granite_configured() -> bool:
    """Return True if Granite configuration is populated in core settings."""
    return settings.is_granite_configured
