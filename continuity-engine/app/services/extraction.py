"""
Granite powered fact extraction pipeline.

Converts screenplay intelligence into
VERSE knowledge graph facts.
"""

import uuid

from app.services.retry import retry_with_backoff
from app.models.schemas import (
    Fact,
    EntityRef,
    SourceRef,
    SourceType,
    EntityType,
)


class GraniteFactExtractor:

    def __init__(self, granite_client):

        self.client = granite_client


    @retry_with_backoff(
        retries=3
    )
    def extract_scene_facts(
        self,
        scene_text: str,
        scene_id: str | None = None,
    ):

        prompt = f"""
You are a film continuity intelligence engine.

Extract facts from this screenplay scene.

Return JSON:

{{
 "facts":[
   {{
    "entity":"character or object",
    "type":"character|prop|costume|lighting",
    "attribute":"state",
    "value":"description",
    "confidence":0.0
   }}
 ]
}}

Scene:

{scene_text}
"""

        result = self.client.generate(prompt)

        facts = []

        for item in result.get(
            "facts",
            []
        ):

            facts.append(
                Fact(

                    fact_id=str(
                        uuid.uuid4()
                    ),

                    entity=EntityRef(

                        type=self._map_type(
                            item.get("type")
                        ),

                        name=item.get(
                            "entity",
                            "unknown"
                        ),
                    ),

                    attribute=item.get(
                        "attribute",
                        "unknown"
                    ),

                    value=item.get(
                        "value"
                    ),

                    scene_id=scene_id,

                    source=SourceRef(
                        type=SourceType.AI_INFERENCE,
                        extractor="ibm-granite"
                    ),

                    confidence=item.get(
                        "confidence",
                        0.8
                    )
                )
            )

        return facts


    def _map_type(
        self,
        value: str | None
    ):

        mapping = {

            "character":
                EntityType.CHARACTER,

            "prop":
                EntityType.PROP,

            "costume":
                EntityType.COSTUME,

            "lighting":
                EntityType.LIGHTING,
        }

        return mapping.get(
            value,
            EntityType.CUSTOM
        )
