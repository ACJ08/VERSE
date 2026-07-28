"""Generic COCO-pretrained YOLO object detector.

Runs a single forward pass per frame across whatever classes are requested
(person + prop classes together), rather than one pass per class, since
they share the same underlying model.
"""

from dataclasses import dataclass

import numpy as np
from ultralytics import YOLO

Bbox = tuple[float, float, float, float]


@dataclass
class Detection:
    class_id: int
    class_name: str
    bbox: Bbox  # x1, y1, x2, y2 in pixels
    confidence: float


class ObjectDetector:
    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        conf_threshold: float = 0.5,
        iou_threshold: float = 0.45,
    ):
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold

    def detect(self, image: np.ndarray, classes: list[int]) -> list[Detection]:
        results = self.model.predict(
            source=image,
            classes=classes,
            conf=self.conf_threshold,
            iou=self.iou_threshold,
            verbose=False,
        )
        detections: list[Detection] = []
        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                detections.append(
                    Detection(
                        class_id=class_id,
                        class_name=self.model.names[class_id],
                        bbox=tuple(box.xyxy[0].tolist()),
                        confidence=float(box.conf[0]),
                    )
                )
        return detections
