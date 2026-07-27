"""Associate a detected prop with the nearest wrist: left / right / both / none."""

import math

from src.pose_estimator import Point, WristPositions


def _distance(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


#  Sane hand-to-prop distance cap. Clean, visually-correct frames (person and
#  glass both clearly in frame) observed distances of 174-656px; the garbage
#  pose estimates seen on hard frames were 1297-1930px -- an order of
#  magnitude further, and often paired with off-frame coordinates. 800px sits
#  comfortably above the clean range with headroom for natural variation,
#  while staying well below the smallest garbage value.
MAX_HAND_DISTANCE_PX = 800.0


def classify_hand_usage(
    prop_center: Point,
    wrists: WristPositions,
    both_tolerance_ratio: float = 0.2,
    max_distance: float = MAX_HAND_DISTANCE_PX,
) -> tuple[str, float | None, float | None]:
    """Return (hand_usage, dist_left, dist_right); a distance is None when that wrist wasn't detected
    or was rejected (out of frame, or farther than `max_distance` from the prop).

    both_tolerance_ratio: if the farther wrist distance is within this fraction
    of the closer one, the prop is treated as roughly centered between both
    wrists ("both") rather than arbitrarily picking the marginally closer side.
    """
    dist_left = _distance(prop_center, wrists.left) if wrists.left else None
    dist_right = _distance(prop_center, wrists.right) if wrists.right else None

    if dist_left is not None and dist_left > max_distance:
        dist_left = None
    if dist_right is not None and dist_right > max_distance:
        dist_right = None

    if dist_left is None and dist_right is None:
        return "none", None, None
    if dist_left is None:
        return "right", None, dist_right
    if dist_right is None:
        return "left", dist_left, None

    closer, farther = min(dist_left, dist_right), max(dist_left, dist_right)
    if farther - closer <= both_tolerance_ratio * closer:
        return "both", dist_left, dist_right
    return ("left" if dist_left < dist_right else "right"), dist_left, dist_right
