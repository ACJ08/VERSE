"""Best-effort costume estimate: dominant torso color mapped to a named color.

Not garment-aware (no clothing segmentation) -- just the median color of a
crop roughly over the torso, snapped to the nearest name in a small palette.
Good enough as a rough continuity signal ("green shirt" vs "red shirt"), not
a precise color match.
"""

import numpy as np

Bbox = tuple[float, float, float, float]

# BGR (OpenCV order) -> name
_NAMED_COLORS: dict[str, tuple[int, int, int]] = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "gray": (128, 128, 128),
    "red": (0, 0, 255),
    "maroon": (0, 0, 128),
    "orange": (0, 165, 255),
    "yellow": (0, 255, 255),
    "olive": (0, 128, 128),
    "green": (0, 128, 0),
    "dark green": (0, 100, 0),
    "teal": (128, 128, 0),
    "cyan": (255, 255, 0),
    "blue": (255, 0, 0),
    "navy": (128, 0, 0),
    "purple": (128, 0, 128),
    "pink": (203, 192, 255),
    "brown": (42, 42, 165),
    "beige": (220, 245, 245),
}


def torso_crop(image: np.ndarray, bbox: Bbox) -> np.ndarray:
    x1, y1, x2, y2 = bbox
    w, h = x2 - x1, y2 - y1
    # vertical band below the head, horizontal band inset from the box edges
    ty1, ty2 = y1 + h * 0.35, y1 + h * 0.75
    tx1, tx2 = x1 + w * 0.15, x1 + w * 0.85
    x1i, y1i = max(int(tx1), 0), max(int(ty1), 0)
    x2i, y2i = int(tx2), int(ty2)
    return image[y1i:y2i, x1i:x2i]


def dominant_color_name(crop: np.ndarray) -> str | None:
    if crop.size == 0:
        return None
    pixels = crop.reshape(-1, 3).astype(np.float32)
    median_bgr = np.median(pixels, axis=0)

    best_name, best_dist = None, float("inf")
    for name, bgr in _NAMED_COLORS.items():
        dist = float(np.linalg.norm(median_bgr - np.array(bgr, dtype=np.float32)))
        if dist < best_dist:
            best_name, best_dist = name, dist
    return best_name
