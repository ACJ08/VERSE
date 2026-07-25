"""
VERSE – Continuity Script Intelligence
app/granite.py

IBM Granite 4.1 integration layer for watsonx.ai.

Architecture
------------
``GraniteClient``
    Singleton-style class that manages:
    * IBM IAM token acquisition and automatic refresh.
    * Prompt construction for scene continuity extraction.
    * Structured JSON output parsing with Pydantic validation.
    * Retry logic with exponential back-off for transient HTTP errors.

``analyse_scene(scene_text, scene_id)``
    Module-level convenience function that instantiates the client on
    first call (lazy singleton) and delegates to it.

Environment variables
---------------------
IBM_API_KEY   – IBM Cloud API key (required).
IBM_URL       – Watsonx.ai regional endpoint (default: us-south).
IBM_PROJECT_ID – Watsonx.ai project ID (required for generation).

Token caching
-------------
IAM tokens are valid for ~1 hour.  The client caches the token and its
expiry timestamp and refreshes it transparently before it expires.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from threading import Lock
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter, Retry

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

# IBM IAM token endpoint
_IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"

# Granite 4.1 model identifier on watsonx.ai
_MODEL_ID = "ibm/granite-4-0-tiny-preview"   # swap to granite-4.1-8b etc. once GA

# Watsonx generation API path
_GENERATE_PATH = "/ml/v1/text/generation?version=2023-05-29"

# Token safety margin: refresh 5 minutes before expiry
_TOKEN_REFRESH_MARGIN_SECS = 300

# Max characters sent per scene (keeps prompt within ~4 k tokens)
_MAX_SCENE_CHARS = 3_000

# Retry configuration for transient HTTP errors
_RETRY_CONFIG = Retry(
    total=3,
    backoff_factor=0.8,
    status_forcelist={429, 500, 502, 503, 504},
    allowed_methods={"POST"},
    raise_on_status=False,
)

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
    Manages communication with the IBM watsonx.ai Granite 4.1 endpoint.

    Parameters
    ----------
    api_key:
        IBM Cloud API key.  Falls back to the ``IBM_API_KEY`` environment
        variable if not supplied.
    project_id:
        Watsonx.ai project ID.  Falls back to ``IBM_PROJECT_ID``.
    base_url:
        Watsonx.ai regional endpoint.  Falls back to ``IBM_URL``.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self._api_key: str = api_key or os.getenv("IBM_API_KEY", "")
        self._project_id: str = project_id or os.getenv("IBM_PROJECT_ID", "")
        self._base_url: str = (
            base_url
            or os.getenv("IBM_URL", "https://us-south.ml.cloud.ibm.com")
        ).rstrip("/")

        if not self._api_key:
            logger.warning(
                "IBM_API_KEY is not set. GraniteClient will raise errors on use."
            )

        # --- IAM token cache -------------------------------------------------
        self._token: str = ""
        self._token_expires_at: float = 0.0
        self._token_lock = Lock()

        # --- Requests session with retry adapter -----------------------------
        self._session = requests.Session()
        adapter = HTTPAdapter(max_retries=_RETRY_CONFIG)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

    # ------------------------------------------------------------------
    # IAM token management
    # ------------------------------------------------------------------

    def _is_token_valid(self) -> bool:
        """Return True if the cached token is still usable."""
        return bool(self._token) and time.time() < (
            self._token_expires_at - _TOKEN_REFRESH_MARGIN_SECS
        )

    def _refresh_token(self) -> None:
        """
        Acquire a new IAM bearer token from IBM Cloud.

        Raises
        ------
        RuntimeError
            When ``IBM_API_KEY`` is missing or the IAM call fails.
        """
        if not self._api_key:
            raise RuntimeError(
                "Cannot acquire IAM token: IBM_API_KEY is not configured."
            )

        logger.debug("Refreshing IBM IAM token …")

        try:
            resp = self._session.post(
                _IAM_TOKEN_URL,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                    "apikey": self._api_key,
                },
                timeout=20,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"IAM token refresh failed: {exc}") from exc

        payload: dict[str, Any] = resp.json()
        self._token = payload["access_token"]
        # ``expires_in`` is the lifetime in seconds from now
        self._token_expires_at = time.time() + payload.get("expires_in", 3600)
        logger.info("IAM token acquired (expires in %ss).", payload.get("expires_in"))

    def _get_token(self) -> str:
        """Return a valid IAM bearer token, refreshing if necessary."""
        with self._token_lock:
            if not self._is_token_valid():
                self._refresh_token()
            return self._token

    # ------------------------------------------------------------------
    # Core generation call
    # ------------------------------------------------------------------

    def _call_generation_api(self, prompt: str) -> str:
        """
        Call the watsonx.ai text generation endpoint.

        Parameters
        ----------
        prompt:
            The fully assembled prompt string.

        Returns
        -------
        str
            Raw generated text from the model.

        Raises
        ------
        RuntimeError
            When the API returns a non-2xx status code.
        """
        url = self._base_url + _GENERATE_PATH
        headers = {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        body = {
            "model_id": _MODEL_ID,
            "project_id": self._project_id,
            "input": prompt,
            "parameters": {
                # Use greedy decoding for deterministic JSON output
                "decoding_method": "greedy",
                "max_new_tokens": 1_024,
                "stop_sequences": [],
                "repetition_penalty": 1.05,
            },
        }

        try:
            resp = self._session.post(url, headers=headers, json=body, timeout=60)
        except requests.RequestException as exc:
            raise RuntimeError(f"Watsonx.ai request failed: {exc}") from exc

        if not resp.ok:
            raise RuntimeError(
                f"Watsonx.ai returned HTTP {resp.status_code}: {resp.text[:400]}"
            )

        data: dict[str, Any] = resp.json()

        # Navigate the watsonx response envelope
        try:
            generated_text: str = data["results"][0]["generated_text"]
        except (KeyError, IndexError) as exc:
            raise RuntimeError(
                f"Unexpected Watsonx response structure: {data}"
            ) from exc

        return generated_text

    # ------------------------------------------------------------------
    # JSON extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_json_block(text: str) -> dict[str, Any]:
        """
        Extract a JSON object from model output.

        The model is instructed to return raw JSON, but it may sometimes
        wrap the response in a code-fence.  This method strips the fence
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
            For unconfigured credentials or API-level failures.
        ValueError
            When the model's output cannot be parsed as valid JSON.
        """
        # --- build prompt ----------------------------------------------------
        prompt = f"{_SYSTEM_PROMPT}\n\n{_build_user_prompt(scene_text)}"

        # --- call model ------------------------------------------------------
        logger.info("Sending scene '%s' to Granite for analysis.", scene_id)
        raw_output: str = self._call_generation_api(prompt)
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
    Return ``True`` when the minimum required environment variables are set.

    Used by the ``/health`` endpoint to report integration status without
    making a live API call.
    """
    return bool(os.getenv("IBM_API_KEY")) and bool(os.getenv("IBM_PROJECT_ID"))