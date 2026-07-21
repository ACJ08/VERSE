"""Screenplay timeline.

Scenes are filmed out of order but reasoned about in screenplay order. This
module owns that ordering and the notion of "narrative proximity", which the
conflict detector uses to weight nearby scenes more heavily than distant ones.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(order=True)
class SceneNode:
    sequence: int
    scene_id: str = field(compare=False)
    label: str = field(default="", compare=False)


class Timeline:
    """Ordered list of scenes with proximity queries.

    Sequence numbers come from the producer when present; otherwise they are
    derived from the scene id (SCENE_012 -> 12) and finally from insertion order.
    """

    def __init__(self) -> None:
        self._scenes: dict[str, SceneNode] = {}
        self._next_fallback = 0

    def add(self, scene_id: str, sequence: int | None = None, label: str = "") -> SceneNode:
        if scene_id in self._scenes:
            node = self._scenes[scene_id]
            # A later payload may supply the authoritative sequence number.
            if sequence is not None and node.sequence != sequence:
                node.sequence = sequence
            return node

        resolved = sequence if sequence is not None else self._infer_sequence(scene_id)
        node = SceneNode(sequence=resolved, scene_id=scene_id, label=label)
        self._scenes[scene_id] = node
        return node

    def _infer_sequence(self, scene_id: str) -> int:
        digits = re.findall(r"\d+", scene_id)
        if digits:
            return int(digits[-1])
        self._next_fallback += 1
        return self._next_fallback

    # -- queries ------------------------------------------------------------ #

    def sequence_of(self, scene_id: str | None) -> int:
        if scene_id is None or scene_id not in self._scenes:
            return 0
        return self._scenes[scene_id].sequence

    def ordered(self) -> list[SceneNode]:
        return sorted(self._scenes.values())

    def earlier_than(self, scene_id: str) -> list[SceneNode]:
        """All scenes that precede `scene_id` in screenplay order, nearest first."""
        target = self.sequence_of(scene_id)
        earlier = [n for n in self._scenes.values() if n.sequence < target]
        return sorted(earlier, key=lambda n: target - n.sequence)

    def proximity(self, scene_a: str | None, scene_b: str | None) -> float:
        """Narrative closeness in (0, 1]. Same scene = 1.0, decaying with distance.

        Used to down-weight evidence from far-away scenes rather than ignore it.
        """
        if scene_a is None or scene_b is None:
            return 0.5
        distance = abs(self.sequence_of(scene_a) - self.sequence_of(scene_b))
        return 1.0 / (1.0 + distance)

    def __contains__(self, scene_id: object) -> bool:
        return scene_id in self._scenes

    def __len__(self) -> int:
        return len(self._scenes)
