"""Screenplay upload endpoint — accepts PDF/TXT/FDX, ingests into the engine.

Extraction pipeline:
1. If IBM Granite (watsonx) is configured, the raw screenplay text is sent to
   the LLM for structured scene extraction — this gives the best results.
2. If Granite is unavailable (no credentials or import error), the endpoint
   falls back to a regex/heuristic parser that handles standard INT./EXT.
   screenplay headings.
"""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.projects import get_or_create_engine
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/upload", tags=["upload"])

_ALLOWED = {
    "application/pdf", "text/plain",
    "application/octet-stream",
    "text/x-fountain", "application/xml",
}
_MAX_SIZE_MB = 20


def _extract_text(filename: str, data: bytes) -> str:
    """Extract plain text from uploaded screenplay."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "pdf":
        try:
            import io
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            raise HTTPException(
                422,
                "PDF parsing requires pypdf. Install it: pip install pypdf. "
                "Alternatively upload a .txt or .fountain file."
            )
    try:
        return data.decode("utf-8", errors="replace")
    except Exception as exc:
        raise HTTPException(422, f"Could not read file: {exc}")


# ─── Granite-based extractor ──────────────────────────────────────────────────

def _granite_extract(text: str, project_id: str) -> dict | None:
    """
    Use IBM Granite to extract structured scenes from raw screenplay text.
    Returns a script-JSON dict on success, or None if Granite is unavailable.
    """
    try:
        from app.services.watsonx import WatsonxAdapter
        llm = WatsonxAdapter()
        if not llm.is_available:
            return None
    except ImportError:
        return None

    # Truncate to avoid token limits — first 8000 chars covers ~40 scenes
    excerpt = text[:8000]

    prompt = f"""You are a screenplay analysis assistant. Extract structured scene data from the screenplay excerpt below.

Return ONLY valid JSON with this exact structure (no markdown, no explanation):
{{
  "scenes": [
    {{
      "scene_id": "SCENE_001",
      "sequence": 1,
      "location": "<INT/EXT location - time>",
      "time_of_day": "<DAY|NIGHT|DUSK|DAWN>",
      "action": "<brief action description, max 300 chars>",
      "characters": [
        {{"name": "<CHARACTER NAME>", "type": "character"}}
      ],
      "props": [
        {{"name": "<prop name>", "type": "prop"}}
      ]
    }}
  ]
}}

Rules:
- scene_id must be SCENE_001, SCENE_002, etc.
- sequence must be an integer starting at 1
- characters: only characters who appear in the scene
- props: only objects explicitly mentioned in the action
- If uncertain, omit the field rather than guessing

SCREENPLAY:
{excerpt}

JSON:"""

    raw = llm(prompt)
    if not raw:
        return None

    # Extract the JSON block from the response (LLM may include surrounding text)
    json_match = re.search(r"\{[\s\S]*\}", raw)
    if not json_match:
        return None

    try:
        import json
        result = json.loads(json_match.group())
        if isinstance(result.get("scenes"), list) and result["scenes"]:
            result["project_id"] = project_id
            result["source"] = "script"
            return result
    except (ValueError, KeyError):
        pass

    return None


# ─── Heuristic fallback parser ────────────────────────────────────────────────

def _heuristic_extract(text: str, project_id: str) -> dict:
    """
    Regex/heuristic screenplay → structured JSON.
    Handles standard INT./EXT. headings.
    Used when Granite is unavailable.
    """
    scenes = []
    heading_re = re.compile(
        r"^(INT\.|EXT\.|I/E\.|INT/EXT\.)[^\n]+", re.IGNORECASE | re.MULTILINE
    )
    positions = [m.start() for m in heading_re.finditer(text)] + [len(text)]

    for i, start in enumerate(positions[:-1]):
        end = positions[i + 1]
        block = text[start:end].strip()
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue

        heading = lines[0]
        action_text = " ".join(lines[1:])[:500]

        time_of_day = "DAY"
        for marker in ("NIGHT", "DUSK", "DAWN", "MORNING", "EVENING", "AFTERNOON"):
            if marker in heading.upper():
                time_of_day = marker
                break

        character_names = list({
            ln for ln in lines[1:]
            if ln.isupper() and 2 < len(ln) < 40 and not ln.startswith("(")
        })

        scene_id = f"SCENE_{i + 1:03d}"
        scenes.append({
            "scene_id": scene_id,
            "sequence": i + 1,
            "location": heading,
            "time_of_day": time_of_day,
            "action": action_text,
            "characters": [{"name": n, "type": "character"} for n in character_names],
            "props": [],
        })

    return {"project_id": project_id, "source": "script", "scenes": scenes}


def _screenplay_to_json(text: str, project_id: str) -> dict:
    """Try Granite first; fall back to heuristic parser."""
    result = _granite_extract(text, project_id)
    if result is not None:
        return result
    return _heuristic_extract(text, project_id)


@router.post("/screenplay")
async def upload_screenplay(
    current_user: Annotated[dict, Depends(get_current_user)],
    project_id: str = Form(...),
    file: UploadFile = File(...),
):
    if file.size and file.size > _MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {_MAX_SIZE_MB} MB limit.")

    data = await file.read()
    if len(data) == 0:
        raise HTTPException(400, "Uploaded file is empty.")

    text = _extract_text(file.filename or "script.txt", data)
    script_json = _screenplay_to_json(text, project_id)

    if not script_json["scenes"]:
        raise HTTPException(
            422,
            "No scene headings found. Ensure the file uses standard screenplay format "
            "(INT./EXT. headings). You can also use the JSON ingest endpoint directly."
        )

    engine = get_or_create_engine(project_id)
    facts = engine.ingest_script(script_json)
    stats = engine.stats()

    return {
        "project_id": project_id,
        "filename": file.filename,
        "scenes_detected": len(script_json["scenes"]),
        "facts_ingested": len(facts),
        "graph_stats": stats,
    }
