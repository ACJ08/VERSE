"""
VERSE API v1 - Single Scene Endpoints.
"""

from fastapi import APIRouter
from app.llm.granite_client import analyse_scene as granite_analyse_scene, is_granite_configured
from app.core.errors import InferenceError
from app.schemas.requests import AnalyseSceneRequest
from app.schemas.continuity import SceneContinuity

router = APIRouter(tags=["Scene Intelligence"])


@router.post(
    "/analyse-scene",
    response_model=SceneContinuity,
    summary="Analyse a single screenplay scene",
    description="Accept raw scene text in the JSON request body and return structured SceneContinuity object.",
)
async def analyse_scene_endpoint(
    request: AnalyseSceneRequest,
) -> SceneContinuity:
    """Stateless single scene continuity analysis endpoint."""
    if not is_granite_configured():
        raise InferenceError(
            "Local Granite server is not configured. Set GRANITE_BASE_URL and GRANITE_MODEL in environment.",
            status_code=503,
        )

    scene_id = request.scene_id or "SCENE_001"
    return granite_analyse_scene(scene_text=request.scene_text, scene_id=scene_id)
