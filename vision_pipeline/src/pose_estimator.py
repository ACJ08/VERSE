"""MediaPipe Pose (Tasks API) wrapper: extract left/right wrist pixel positions.

Runs on the full frame with num_poses=1 -- adequate for this single-person
clip. For a multi-person scene this would need per-person ROI cropping to
avoid attributing the wrong body's wrists to a tracked person; that's a known
simplification, not handled here.
"""

from dataclasses import dataclass

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python.core.base_options import BaseOptions

LEFT_WRIST = mp_vision.PoseLandmark.LEFT_WRIST
RIGHT_WRIST = mp_vision.PoseLandmark.RIGHT_WRIST

Point = tuple[float, float]


@dataclass
class WristPositions:
    left: Point | None
    right: Point | None


class PoseEstimator:
    def __init__(
        self,
        model_path: str = "pose_landmarker_lite.task",
        min_confidence: float = 0.1,
        min_visibility: float = 0.3,
    ):
        base_options = BaseOptions(model_asset_path=model_path)
        options = mp_vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=min_confidence,
            min_pose_presence_confidence=min_confidence,
        )
        self._landmarker = mp_vision.PoseLandmarker.create_from_options(options)
        self.min_visibility = min_visibility

    def wrists(self, image_bgr: np.ndarray) -> WristPositions:
        height, width = image_bgr.shape[:2]
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
        result = self._landmarker.detect(mp_image)

        if not result.pose_landmarks:
            return WristPositions(left=None, right=None)

        landmarks = result.pose_landmarks[0]

        def px(index: int) -> Point | None:
            lm = landmarks[index]
            if lm.visibility < self.min_visibility:
                return None
            x, y = lm.x * width, lm.y * height
            # Plausibility gate: a landmark projected outside the actual frame
            # is a low-quality guess, not a real detection -- reject it rather
            # than let it drive a hand association.
            if x < 0 or x >= width or y < 0 or y >= height:
                return None
            return (x, y)

        return WristPositions(left=px(LEFT_WRIST), right=px(RIGHT_WRIST))
