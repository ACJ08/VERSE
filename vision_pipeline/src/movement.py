"""Movement classification from bounding-box center delta between consecutive tracked frames."""

import math

Point = tuple[float, float]


def center_delta(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def classify_movement(delta_px: float, threshold_px: float) -> str:
    return "moving" if delta_px > threshold_px else "stationary"
