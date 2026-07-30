"""Explicit greedy IoU-based deduplication, applied on top of the detector's
internal NMS as a safety net -- overlapping same-class boxes on one physical
object (e.g. a fragmented person detection) collapse into the highest-confidence
box.
"""

from src.object_detector import Detection


def iou(box_a: tuple[float, float, float, float], box_b: tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    inter_x1, inter_y1 = max(ax1, bx1), max(ay1, by1)
    inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
    inter_area = max(0.0, inter_x2 - inter_x1) * max(0.0, inter_y2 - inter_y1)
    if inter_area == 0.0:
        return 0.0

    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter_area / (area_a + area_b - inter_area)


def deduplicate(detections: list[Detection], iou_threshold: float = 0.45) -> list[Detection]:
    kept: list[Detection] = []
    for class_id in {d.class_id for d in detections}:
        remaining = sorted((d for d in detections if d.class_id == class_id), key=lambda d: -d.confidence)
        while remaining:
            best = remaining.pop(0)
            kept.append(best)
            remaining = [d for d in remaining if iou(best.bbox, d.bbox) < iou_threshold]
    return kept
