"""Geometry helpers for mapping detections to screen-space semantics."""

Bbox = tuple[float, float, float, float]


def bbox_center(bbox: Bbox) -> tuple[float, float]:
    x1, y1, x2, y2 = bbox
    return (x1 + x2) / 2, (y1 + y2) / 2


def screen_position(center_x: float, frame_width: int) -> str:
    """Classify horizontal position as left/center/right by frame thirds."""
    fraction = center_x / frame_width
    if fraction < 1 / 3:
        return "left"
    if fraction > 2 / 3:
        return "right"
    return "center"
