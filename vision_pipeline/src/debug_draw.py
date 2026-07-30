"""Debug visualization: draw detection boxes, wrists, and prop centers onto a frame image."""

import cv2
import numpy as np

from src.coco_classes import PERSON
from src.object_detector import Detection
from src.pose_estimator import Point, WristPositions

PERSON_COLOR = (0, 255, 0)  # green, BGR
PROP_COLOR = (255, 128, 0)  # blue, BGR
WRIST_COLOR = (0, 0, 255)  # red, BGR
GLASS_CENTER_COLOR = (0, 255, 255)  # yellow, BGR


def draw_detections(image: np.ndarray, detections: list[Detection]) -> np.ndarray:
    annotated = image.copy()
    for det in detections:
        x1, y1, x2, y2 = (int(v) for v in det.bbox)
        color = PERSON_COLOR if det.class_id == PERSON else PROP_COLOR
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
        label = f"{det.class_name} {det.confidence:.2f}"
        cv2.putText(
            annotated, label, (x1, max(y1 - 8, 0)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA,
        )
    return annotated


def draw_wrists(image: np.ndarray, wrists: WristPositions) -> np.ndarray:
    annotated = image
    for point, label in ((wrists.left, "L wrist"), (wrists.right, "R wrist")):
        if point is None:
            continue
        x, y = int(point[0]), int(point[1])
        cv2.circle(annotated, (x, y), 10, WRIST_COLOR, -1)
        cv2.putText(annotated, label, (x + 12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, WRIST_COLOR, 2, cv2.LINE_AA)
    return annotated


def draw_prop_center(image: np.ndarray, center: Point, label: str) -> np.ndarray:
    x, y = int(center[0]), int(center[1])
    cv2.drawMarker(image, (x, y), GLASS_CENTER_COLOR, markerType=cv2.MARKER_CROSS, markerSize=24, thickness=3)
    cv2.putText(
        image, label, (x + 12, y + 20),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, GLASS_CENTER_COLOR, 2, cv2.LINE_AA,
    )
    return image
