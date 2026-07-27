"""Frame extraction from video via OpenCV, sampled at a target fps."""

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class ExtractedFrame:
    frame_id: int
    source_frame_index: int
    timestamp: float
    image: np.ndarray


def extract_frames(video_path: str, target_fps: float = 2.0) -> tuple[list[ExtractedFrame], float]:
    """Sample frames from `video_path` at approximately `target_fps`.

    Returns (frames, source_fps). Sampling is done by stepping through
    source frames at a fixed interval rather than seeking, since frame-accurate
    seeking is unreliable across codecs.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video: {video_path}")

    source_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_interval = max(1, round(source_fps / target_fps))

    frames: list[ExtractedFrame] = []
    source_index = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if source_index % frame_interval == 0:
            timestamp = source_index / source_fps
            frames.append(
                ExtractedFrame(
                    frame_id=len(frames),
                    source_frame_index=source_index,
                    timestamp=round(timestamp, 3),
                    image=frame,
                )
            )
        source_index += 1

    cap.release()
    return frames, source_fps
