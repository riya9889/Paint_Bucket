"""Draws OCR boxes on the live video."""
from typing import List

import cv2
import numpy as np

from .models import Detection

_COLORS = {            # BGR
    "pass": (0, 200, 0),
    "reject": (0, 0, 230),
}
_DEFAULT = (0, 190, 255)


def draw_detections(frame: np.ndarray, detections: List[Detection], status: str) -> np.ndarray:
    color = _COLORS.get(status, _DEFAULT)
    for det in detections:
        pts = np.array(det.box, dtype=np.int32).reshape((-1, 1, 2))
        cv2.polylines(frame, [pts], True, color, 2)
        x, y = det.box[0]
        label = f"{det.text} ({det.confidence:.0%})"
        cv2.putText(frame, label, (x, max(15, y - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)
    return frame