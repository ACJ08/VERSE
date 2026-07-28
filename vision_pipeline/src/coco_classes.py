"""COCO class ids used by the pipeline (subset of the 80-class Ultralytics list)."""

PERSON = 0
WINE_GLASS = 40
CUP = 41

PROP_CLASSES: dict[int, str] = {
    WINE_GLASS: "wine glass",
    CUP: "cup",
}
