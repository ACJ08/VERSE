"""Simple frame-to-frame person tracker: greedy nearest-centroid matching.

Not a full SORT/Kalman tracker -- adequate for a slow-moving single/few-person
shot at ~2fps sampling. A detection matches the closest existing track within
`max_distance` pixels; unmatched detections start new tracks; tracks missing
for more than `max_frames_missing` sampled frames are dropped.
"""

from dataclasses import dataclass

from src.geometry import bbox_center
from src.object_detector import Bbox, Detection


@dataclass
class _Track:
    track_id: int
    bbox: Bbox
    last_seen_frame: int


class CentroidTracker:
    def __init__(self, max_distance: float = 150.0, max_frames_missing: int = 5):
        self.max_distance = max_distance
        self.max_frames_missing = max_frames_missing
        self._tracks: dict[int, _Track] = {}
        self._next_id = 1

    def update(self, frame_index: int, detections: list[Detection]) -> list[int]:
        """Return a stable track_id per detection, in the same order as `detections`."""
        stale_ids = [
            tid
            for tid, track in self._tracks.items()
            if frame_index - track.last_seen_frame > self.max_frames_missing
        ]
        for tid in stale_ids:
            del self._tracks[tid]

        det_centers = [bbox_center(d.bbox) for d in detections]
        candidate_pairs = []
        for tid, track in self._tracks.items():
            tcx, tcy = bbox_center(track.bbox)
            for i, (cx, cy) in enumerate(det_centers):
                dist = ((cx - tcx) ** 2 + (cy - tcy) ** 2) ** 0.5
                if dist <= self.max_distance:
                    candidate_pairs.append((dist, tid, i))
        candidate_pairs.sort(key=lambda p: p[0])

        assigned: list[int | None] = [None] * len(detections)
        used_tracks: set[int] = set()
        used_dets: set[int] = set()
        for _dist, tid, i in candidate_pairs:
            if tid in used_tracks or i in used_dets:
                continue
            assigned[i] = tid
            used_tracks.add(tid)
            used_dets.add(i)
            self._tracks[tid].bbox = detections[i].bbox
            self._tracks[tid].last_seen_frame = frame_index

        for i, det in enumerate(detections):
            if assigned[i] is None:
                tid = self._next_id
                self._next_id += 1
                self._tracks[tid] = _Track(track_id=tid, bbox=det.bbox, last_seen_frame=frame_index)
                assigned[i] = tid

        return assigned  # type: ignore[return-value]
