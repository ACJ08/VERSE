"""
VERSE – Continuity Script Intelligence
app/granite.py

Local IBM Granite 4.1 integration layer using an OpenAI-compatible API client.

Architecture
------------
``GraniteClient``
    Singleton-style class that manages:
    * Connection to local Granite inference server (vLLM, Ollama, etc.) via OpenAI SDK.
    * Prompt construction for scene continuity extraction.
    * Structured JSON output parsing with Pydantic validation.

``analyse_scene(scene_text, scene_id)``
    Module-level convenience function that instantiates the client on
    first call (lazy singleton) and delegates to it.

Environment variables
---------------------
GRANITE_BASE_URL – Local Granite inference server base URL (default: http://localhost:8000/v1).
GRANITE_MODEL    – Local Granite model identifier (default: ibm-granite/granite-4.1).
GRANITE_API_KEY  – API key for inference server (default: EMPTY).
"""

from __future__ import annotations

import json
import logging
import os
import re
from threading import Lock
from typing import Any, Optional

from openai import APIConnectionError, OpenAI, OpenAIError

from app.schema import (
    Character,
    ContinuityNote,
    Lighting,
    Prop,
    SceneContinuity,
    SceneMetadata,
)

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default local Granite inference configuration
_DEFAULT_BASE_URL = "http://localhost:8000/v1"
_DEFAULT_MODEL = "ibm-granite/granite-4.1"

# Max characters sent per scene (keeps prompt within model context window)
_MAX_SCENE_CHARS = 3_000

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a professional script supervisor and continuity analyst for film productions.
Your task is to extract structured continuity data from a single screenplay scene.

Return ONLY a valid JSON object with the following schema (omit null fields):
{
  "characters": [
    {
      "name": "CHARACTER NAME",
      "costume": "description or null",
      "position": "description or null",
      "movement": "description or null",
      "emotional_state": "description or null"
    }
  ],
  "props": [
    {
      "name": "prop name",
      "hand_usage": "left|right|both|none or null",
      "state": "condition or null",
      "owner": "character name or null"
    }
  ],
  "lighting": {
    "description": "overall lighting or null",
    "source": "light source or null",
    "mood": "emotional tone or null",
    "time_of_day": "DAY|NIGHT|DAWN|DUSK or null"
  },
  "continuity_notes": [
    {
      "note": "description of continuity concern",
      "severity": "LOW|MEDIUM|HIGH",
      "category": "WARDROBE|PROP|LIGHTING|MOVEMENT|DIALOGUE|OTHER",
      "affected_characters": ["NAME1"]
    }
  ]
}

Rules:
- Include ONLY characters, props, and details EXPLICITLY mentioned in the scene.
- Extract EVERY prop the character physically interacts with.
- Note hand usage when specified (left hand, right hand, both hands).
- Flag any continuity concerns that a script supervisor should track.
- Do NOT invent information not present in the scene text.
- Respond with raw JSON only — no markdown, no explanations.
"""


def _build_user_prompt(scene_text: str) -> str:
    """Wrap the scene text inside a user-turn prompt."""
    truncated = scene_text[:_MAX_SCENE_CHARS]
    if len(scene_text) > _MAX_SCENE_CHARS:
        truncated += "\n[...scene truncated for length...]"
    return f"Analyse the following screenplay scene:\n\n{truncated}"


# ---------------------------------------------------------------------------
# Granite client
# ---------------------------------------------------------------------------

class GraniteClient:
    """
    Manages communication with local IBM Granite 4.1 OpenAI-compatible endpoint.

    Parameters
    ----------
    base_url:
        Inference server base URL. Falls back to GRANITE_BASE_URL environment variable.
    model:
        Model identifier string. Falls back to GRANITE_MODEL environment variable.
    api_key:
        API key for inference server. Falls back to GRANITE_API_KEY environment variable.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self._base_url: str = (
            base_url
            or os.getenv("GRANITE_BASE_URL", _DEFAULT_BASE_URL)
        ).rstrip("/")
        self._model: str = model or os.getenv("GRANITE_MODEL", _DEFAULT_MODEL)
        self._api_key: str = api_key or os.getenv("GRANITE_API_KEY", "EMPTY")

        self._client = OpenAI(
            base_url=self._base_url,
            api_key=self._api_key,
        )

    # ------------------------------------------------------------------
    # Core generation call
    # ------------------------------------------------------------------

    def _call_generation_api(self, prompt: str) -> str:
        """
        Call the OpenAI-compatible chat completion endpoint.

        Parameters
        ----------
        prompt:
            The user prompt text containing scene details to analyze.

        Returns
        -------
        str
            Raw generated text from the model.

        Raises
        ------
        RuntimeError
            When unable to connect to local Granite inference server or request fails.
        """
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=1024,
            )
            content = response.choices[0].message.content
            if content is None:
                raise RuntimeError("Granite inference server returned empty completion content.")
            return content
        except APIConnectionError as exc:
            logger.error("Failed to connect to Granite server at %s: %s", self._base_url, exc)
            raise RuntimeError(
                f"Unable to connect to Granite inference server at {self._base_url}: {exc}"
            ) from exc
        except OpenAIError as exc:
            logger.error("Granite API request error: %s", exc)
            raise RuntimeError(
                f"Local Granite inference request failed: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # JSON extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_json_block(text: str) -> dict[str, Any]:
        """
        Extract a JSON object from model output.

        The model is instructed to return raw JSON, but it may sometimes
        wrap the response in a code-fence. This method strips the fence
        before parsing.

        Raises
        ------
        ValueError
            When no valid JSON object can be found in the text.
        """
        # Strip markdown code fences if present
        stripped = re.sub(r"```(?:json)?", "", text).strip().strip("`")

        # Find the outermost JSON object
        match = re.search(r"\{.*\}", stripped, re.DOTALL)
        if not match:
            raise ValueError(f"No JSON object found in model output: {text[:200]!r}")

        raw_json = match.group(0)
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Model returned malformed JSON: {exc} | raw: {raw_json[:200]!r}"
            ) from exc

    # ------------------------------------------------------------------
    # Public analysis method
    # ------------------------------------------------------------------

    def analyse_scene(
        self,
        scene_text: str,
        scene_id: str = "SCENE_01",
    ) -> SceneContinuity:
        """
        Extract structured continuity data for one screenplay scene.

        Parameters
        ----------
        scene_text:
            Raw text of the scene (INT./EXT. heading through end of scene).
        scene_id:
            Identifier string used to populate ``SceneMetadata.scene_id``.

        Returns
        -------
        SceneContinuity
            Validated Pydantic model containing all continuity data.

        Raises
        ------
        RuntimeError
            For connectivity failures or server-level errors.
        ValueError
            When the model's output cannot be parsed as valid JSON.
        """
        # --- build user prompt -----------------------------------------------
        user_prompt = _build_user_prompt(scene_text)

        # --- call model ------------------------------------------------------
        logger.info("Sending scene '%s' to local Granite (%s) for analysis.", scene_id, self._model)
        raw_output: str = self._call_generation_api(user_prompt)
        logger.debug("Granite raw output for '%s': %s", scene_id, raw_output[:300])

        # --- parse JSON ------------------------------------------------------
        parsed: dict[str, Any] = self._extract_json_block(raw_output)

        # --- build metadata from scene heading -------------------------------
        metadata = _parse_scene_metadata(scene_text=scene_text, scene_id=scene_id)

        # --- validate sub-models ---------------------------------------------
        characters: list[Character] = [
            Character.model_validate(c)
            for c in parsed.get("characters", [])
        ]
        props: list[Prop] = [
            Prop.model_validate(p)
            for p in parsed.get("props", [])
        ]
        lighting_data = parsed.get("lighting")
        lighting: Optional[Lighting] = (
            Lighting.model_validate(lighting_data) if lighting_data else None
        )
        continuity_notes: list[ContinuityNote] = [
            ContinuityNote.model_validate(n)
            for n in parsed.get("continuity_notes", [])
        ]

        return SceneContinuity(
            metadata=metadata,
            characters=characters,
            props=props,
            lighting=lighting,
            continuity_notes=continuity_notes,
            raw_scene_text=scene_text,
        )


# ---------------------------------------------------------------------------
# Scene heading parser
# ---------------------------------------------------------------------------

# Matches e.g.: "INT. SARAH'S APARTMENT - LIVING ROOM - NIGHT"
_HEADING_RE = re.compile(
    r"^(?P<int_ext>INT\.|EXT\.|INT\./EXT\.|I/E\.)\s+"
    r"(?P<location>[^-\n]+?)"
    r"(?:\s+-\s+(?P<sublocation>[^-\n]+?))?"
    r"(?:\s+-\s+(?P<time>DAY|NIGHT|DAWN|DUSK|CONTINUOUS|LATER|MOMENTS LATER))?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _parse_scene_metadata(scene_text: str, scene_id: str) -> SceneMetadata:
    """
    Parse a ``SceneMetadata`` object from the scene's slug line.

    Falls back to storing the entire first line as ``heading`` when
    the regex does not match.
    """
    first_line = scene_text.strip().splitlines()[0].strip() if scene_text.strip() else ""
    match = _HEADING_RE.match(first_line)

    if match:
        gd = match.groupdict()
        return SceneMetadata(
            scene_id=scene_id,
            heading=first_line,
            interior_exterior=gd["int_ext"].upper() if gd["int_ext"] else None,
            location=gd["location"].strip().upper() if gd["location"] else None,
            sub_location=gd["sublocation"].strip().upper() if gd.get("sublocation") else None,
            time=gd["time"].upper() if gd.get("time") else None,
        )

    # Fallback: store raw heading, leave structured fields empty
    return SceneMetadata(
        scene_id=scene_id,
        heading=first_line or None,
    )


# ---------------------------------------------------------------------------
# Module-level lazy singleton
# ---------------------------------------------------------------------------

_client_instance: Optional[GraniteClient] = None
_client_lock = Lock()


def _get_client() -> GraniteClient:
    """Return the module-level GraniteClient singleton, creating it once."""
    global _client_instance
    with _client_lock:
        if _client_instance is None:
            _client_instance = GraniteClient()
    return _client_instance


def analyse_scene(
    scene_text: str,
    scene_id: str = "SCENE_01",
) -> SceneContinuity:
    """
    Module-level convenience function for scene analysis.

    Instantiates the ``GraniteClient`` singleton on first call and
    delegates to ``GraniteClient.analyse_scene``.

    Parameters
    ----------
    scene_text:
        Raw text of a single screenplay scene.
    scene_id:
        Human-readable scene identifier used in the output JSON.

    Returns
    -------
    SceneContinuity
        Validated continuity model for the scene.
    """
    return _get_client().analyse_scene(scene_text=scene_text, scene_id=scene_id)


def is_granite_configured() -> bool:
    """
    Return ``True`` when the minimum required environment variables or defaults are configured.

    Used by the ``/health`` endpoint to report integration status without
    making a live API call.
    """
    base_url = os.getenv("GRANITE_BASE_URL", _DEFAULT_BASE_URL)
    model = os.getenv("GRANITE_MODEL", _DEFAULT_MODEL)
    return bool(base_url) and bool(model)