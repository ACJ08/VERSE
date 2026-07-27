"""VERSE vision pipeline entry point.

Step 5: final schema output. Emits scene_<id>.json with a top-level scene_id
and an observations array. Each observation carries characters/props matching
the teammate's Pydantic schema exactly, plus a sibling `detections` array for
confidence scores.

Vision-detectable fields are filled in:
  - position: left/center/right from bbox center (step 2)
  - hand_usage: nearest-wrist association, plausibility-gated (step 4)
  - movement: "stationary"/"moving" from bbox-center delta between consecutive
    sampled frames for the same tracked person
  - costume: best-effort dominant torso color name
Not vision-detectable, left null: emotional_state, owner, state.
"""

import argparse
import json
import sys

import cv2

from src.coco_classes import CUP, PERSON, PROP_CLASSES, WINE_GLASS
from src.costume import dominant_color_name, torso_crop
from src.debug_draw import draw_detections, draw_prop_center, draw_wrists
from src.frame_extractor import ExtractedFrame, extract_frames
from src.geometry import bbox_center, screen_position
from src.hand_association import classify_hand_usage
from src.movement import center_delta, classify_movement
from src.nms import deduplicate
from src.object_detector import Detection, ObjectDetector
from src.pose_estimator import PoseEstimator, WristPositions
from src.timecode import format_timestamp
from src.tracker import CentroidTracker

TRACKED_CLASSES = [PERSON, WINE_GLASS, CUP]
MOVEMENT_THRESHOLD_RATIO = 0.015  # fraction of frame diagonal a track must move to count as "moving"


def build_observations(
    frames: list[ExtractedFrame],
    detector: ObjectDetector,
    tracker: CentroidTracker,
    pose_estimator: PoseEstimator,
) -> tuple[list[dict], dict[int, list[Detection]], dict[int, dict]]:
    observations = []
    raw_by_frame: dict[int, list[Detection]] = {}
    hand_debug_by_frame: dict[int, dict] = {}
    prev_center_by_track: dict[int, tuple[float, float]] = {}

    height0, width0 = frames[0].image.shape[:2] if frames else (0, 0)
    movement_threshold_px = MOVEMENT_THRESHOLD_RATIO * (width0**2 + height0**2) ** 0.5

    for frame in frames:
        height, width = frame.image.shape[:2]
        detections = detector.detect(frame.image, classes=TRACKED_CLASSES)
        detections = deduplicate(detections, iou_threshold=0.45)
        raw_by_frame[frame.frame_id] = detections

        person_dets = sorted(
            (d for d in detections if d.class_id == PERSON), key=lambda d: bbox_center(d.bbox)[0]
        )
        prop_dets = [d for d in detections if d.class_id in PROP_CLASSES]

        track_ids = tracker.update(frame.frame_id, person_dets)

        characters = []
        detection_entries = []
        for det, track_id in zip(person_dets, track_ids):
            center = bbox_center(det.bbox)

            movement = None
            prev_center = prev_center_by_track.get(track_id)
            if prev_center is not None:
                movement = classify_movement(center_delta(center, prev_center), movement_threshold_px)
            prev_center_by_track[track_id] = center

            costume = dominant_color_name(torso_crop(frame.image, det.bbox))

            name = f"PERSON_{track_id}"
            characters.append(
                {
                    "name": name,
                    "costume": costume,
                    "position": screen_position(center[0], width),
                    "movement": movement,
                    "emotional_state": None,
                }
            )
            detection_entries.append(
                {"type": "character", "name": name, "confidence": round(det.confidence, 3)}
            )

        # No detected person means no body for a wrist association to come from,
        # regardless of what MediaPipe Pose (which runs independently of YOLO)
        # might report -- force hand_usage to "none" for every prop this frame.
        wrists = (
            pose_estimator.wrists(frame.image)
            if prop_dets and person_dets
            else WristPositions(left=None, right=None)
        )

        props = []
        associations = []
        for det in prop_dets:
            prop_name = PROP_CLASSES[det.class_id]
            prop_center = bbox_center(det.bbox)
            hand_usage, dist_left, dist_right = classify_hand_usage(prop_center, wrists)

            props.append(
                {
                    "name": prop_name,
                    "hand_usage": hand_usage,
                    "state": None,
                    "owner": None,
                }
            )
            detection_entries.append(
                {"type": "prop", "name": prop_name, "confidence": round(det.confidence, 3)}
            )
            associations.append(
                {
                    "prop_name": prop_name,
                    "prop_center": prop_center,
                    "dist_left": dist_left,
                    "dist_right": dist_right,
                    "hand_usage": hand_usage,
                }
            )

        if prop_dets:
            hand_debug_by_frame[frame.frame_id] = {"wrists": wrists, "associations": associations}

        observations.append(
            {
                "frame_id": frame.frame_id,
                "timestamp": format_timestamp(frame.timestamp),
                "characters": characters,
                "props": props,
                "detections": detection_entries,
            }
        )

    return observations, raw_by_frame, hand_debug_by_frame


def save_debug_frame(
    frames: list[ExtractedFrame],
    raw_by_frame: dict[int, list[Detection]],
    hand_debug_by_frame: dict[int, dict],
    out_path: str,
    frame_id: int | None = None,
) -> None:
    if not frames:
        return
    if frame_id is None:
        frame_id = max(raw_by_frame, key=lambda fid: len(raw_by_frame[fid]))
    if frame_id not in raw_by_frame:
        print(f"Warning: frame_id {frame_id} not found; skipping debug frame", file=sys.stderr)
        return

    frame = frames[frame_id]
    annotated = draw_detections(frame.image, raw_by_frame[frame_id])

    hand_debug = hand_debug_by_frame.get(frame_id)
    if hand_debug is not None:
        annotated = draw_wrists(annotated, hand_debug["wrists"])
        for assoc in hand_debug["associations"]:
            label = f"{assoc['prop_name']} center -> {assoc['hand_usage']}"
            annotated = draw_prop_center(annotated, assoc["prop_center"], label)

    cv2.imwrite(out_path, annotated)
    n_det = len(raw_by_frame[frame_id])
    print(f"Saved debug frame (frame_id={frame_id}, {n_det} detection(s)) to {out_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="VERSE footage-processing pipeline")
    parser.add_argument("--video", required=True, help="Path to input video clip")
    parser.add_argument("--scene-id", required=True, help="Scene identifier applied to every observation, e.g. SCENE_001")
    parser.add_argument("--fps", type=float, default=2.0, help="Target sampling rate in frames/sec")
    parser.add_argument("--out", default=None, help="Output JSON path (default: scene_<id>.json, lowercased)")
    parser.add_argument("--model", default="yolov8n.pt", help="Ultralytics YOLO model weights")
    parser.add_argument("--pose-model", default="pose_landmarker_lite.task", help="MediaPipe pose model bundle")
    parser.add_argument("--conf", type=float, default=0.5, help="Minimum detection confidence")
    parser.add_argument("--iou", type=float, default=0.45, help="IoU threshold for deduplication")
    parser.add_argument("--debug-out", default="debug_frame.jpg", help="Path to write annotated debug frame")
    parser.add_argument(
        "--debug-frame-id", type=int, default=None,
        help="Specific frame_id to save as the debug frame (defaults to the frame with the most detections)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        frames, source_fps = extract_frames(args.video, target_fps=args.fps)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Video: {args.video}")
    print(f"Source FPS: {source_fps:.2f}")
    print(f"Extracted {len(frames)} frames")

    detector = ObjectDetector(args.model, conf_threshold=args.conf, iou_threshold=args.iou)
    pose_estimator = PoseEstimator(args.pose_model)
    frame_width = frames[0].image.shape[1] if frames else 0
    tracker = CentroidTracker(max_distance=0.3 * frame_width)

    observations, raw_by_frame, hand_debug_by_frame = build_observations(
        frames, detector, tracker, pose_estimator
    )

    scene_doc = {"scene_id": args.scene_id, "observations": observations}
    out_path = args.out or f"{args.scene_id.lower()}.json"
    with open(out_path, "w") as f:
        json.dump(scene_doc, f, indent=2)

    total_people = sum(len(o["characters"]) for o in observations)
    total_props = sum(len(o["props"]) for o in observations)
    print(f"Detected {total_people} person instance(s) and {total_props} prop instance(s) across {len(frames)} frames")
    print(f"Wrote {out_path}")

    save_debug_frame(frames, raw_by_frame, hand_debug_by_frame, args.debug_out, frame_id=args.debug_frame_id)


if __name__ == "__main__":
    main()
