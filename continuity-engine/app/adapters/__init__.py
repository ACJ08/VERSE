"""Producing-team payload adapters.

The engine accepts arbitrary nested JSON, so nothing here is required to *store*
a payload. What these adapters buy is comparison: they land each team's fields on
the canonical attributes the rules in `app/reasoning/rules.py` actually watch,
and they aggregate team 2's per-frame output into per-scene statements.

    from app.adapters import adapt_any

    adapted = adapt_any(payload)                 # shape detected automatically
    engine.ingest(adapted.payload, adapted.source)

`adapt_any` recognises team 1's script response, team 1's call sheets and
team 2's vision documents, and passes payloads that are already in the engine's
own shape (see `examples/`) straight through.
"""

from __future__ import annotations

from typing import Any

from app.adapters.base import AdaptedPayload
from app.adapters.call_sheet import adapt_call_sheet, looks_like_call_sheet
from app.adapters.script_intelligence import (
    adapt_script_intelligence,
    looks_like_script_intelligence,
)
from app.adapters.vision import adapt_vision, looks_like_vision
from app.models.schemas import SourceType

__all__ = [
    "AdaptedPayload",
    "adapt_any",
    "adapt_call_sheet",
    "adapt_script_intelligence",
    "adapt_vision",
    "detect_shape",
    "looks_like_call_sheet",
    "looks_like_script_intelligence",
    "looks_like_vision",
]


def detect_shape(payload: Any) -> str:
    """Name the payload shape: script_intelligence | vision | call_sheet | engine."""
    if looks_like_script_intelligence(payload):
        return "script_intelligence"
    if looks_like_vision(payload):
        return "vision"
    if looks_like_call_sheet(payload):
        return "call_sheet"
    return "engine"


def adapt_any(
    payload: Any,
    *,
    default_source: SourceType = SourceType.SCRIPT,
    **kwargs: Any,
) -> AdaptedPayload:
    """Adapt a payload of any recognised shape.

    `kwargs` are forwarded to the adapter that matches, so callers can pass
    vision options (`scene_id`, `entity_aliases`, `infer_prop_owner`) without
    knowing in advance which shape arrived. Already-engine-shaped payloads are
    returned untouched under `default_source`.
    """
    shape = detect_shape(payload)
    if shape == "script_intelligence":
        return adapt_script_intelligence(payload, **_only(kwargs, {"scene_prefix"}))
    if shape == "vision":
        return adapt_vision(
            payload,
            **_only(kwargs, {"scene_id", "sequence", "entity_aliases", "infer_prop_owner"}),
        )
    if shape == "call_sheet":
        return adapt_call_sheet(payload, **_only(kwargs, {"scene_prefix"}))

    container = payload if isinstance(payload, dict) else {}
    scenes = container.get("scenes") or container.get("observations") or []
    scene_ids = [
        str(item["scene_id"])
        for item in scenes
        if isinstance(item, dict) and item.get("scene_id") is not None
    ]
    return AdaptedPayload(payload=payload, source=default_source, scene_ids=scene_ids)


def _only(kwargs: dict[str, Any], allowed: set[str]) -> dict[str, Any]:
    return {k: v for k, v in kwargs.items() if k in allowed and v is not None}
