"""EasyOCR wrapper with OpenCV preprocessing. Model loads in the background."""
import threading
from typing import List, Optional

import cv2
import numpy as np

from .models import Detection


class OCREngine:
    def __init__(self, languages: List[str], use_gpu: bool, max_width: int):
        self._languages = languages
        self._use_gpu = use_gpu
        self._max_width = max_width
        self._reader = None
        self._error = ""
        self._thread: Optional[threading.Thread] = None

    @property
    def ready(self) -> bool:
        return self._reader is not None

    @property
    def error(self) -> str:
        return self._error

    def load_async(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._load, daemon=True)
            self._thread.start()

    def _load(self) -> None:
        try:
            import easyocr  # imported here so the web server starts instantly
            self._reader = easyocr.Reader(
                self._languages, gpu=self._use_gpu, verbose=False
            )
        except Exception as exc:  # noqa: BLE001
            self._error = f"EasyOCR failed to load: {exc}"

    def _preprocess(self, frame: np.ndarray):
        h, w = frame.shape[:2]
        scale = min(1.0, self._max_width / float(w))
        if scale < 1.0:
            frame = cv2.resize(frame, (int(w * scale), int(h * scale)),
                               interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(gray), scale

    def read(self, frame: np.ndarray) -> List[Detection]:
        if not self.ready:
            return []
        image, scale = self._preprocess(frame)
        results = self._reader.readtext(image, detail=1, paragraph=False)
        detections = []
        for box, text, conf in results:
            text = str(text).strip()
            if not text:
                continue
            original_box = tuple((int(x / scale), int(y / scale)) for x, y in box)
            detections.append(Detection(text=text, confidence=float(conf),
                                        box=original_box))
        return detections