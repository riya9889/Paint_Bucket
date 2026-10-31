"""Background worker: grabs frames, runs OCR, decides PASS / REJECT."""
import threading
from collections import Counter, deque
from typing import Deque, List, Optional

import config
from .bucket_catalog import BucketCatalog
from .camera import Camera
from .matcher import FrameOutcome, evaluate_frame
from .models import Detection
from .ocr_engine import OCREngine

_UNKNOWN = "__unknown__"


class Verifier:
    def __init__(self, camera: Camera, ocr: OCREngine, catalog: BucketCatalog):
        self._camera = camera
        self._ocr = ocr
        self._catalog = catalog
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._target = ""
        self._history: Deque[Optional[str]] = deque(maxlen=config.HISTORY_SIZE)
        self._detections: List[Detection] = []
        self._state = self._idle_state()

    # ---------- public API ----------
    @staticmethod
    def _idle_state() -> dict:
        return {"status": "idle", "detected_product": "", "detected_texts": [],
                "confidence": 0.0, "message": "Select a bucket and start the webcam."}

    def start(self, target: str) -> None:
        self.set_target(target)
        if self._thread is not None and self._thread.is_alive():
            return
        with self._lock:
            self._history.clear()
            self._detections = []
            self._state = {**self._idle_state(), "status": "scanning",
                           "message": "Scanning… point the label at the camera."}
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3)
            self._thread = None
        with self._lock:
            self._history.clear()
            self._detections = []
            self._state = self._idle_state()

    def set_target(self, target: str) -> None:
        with self._lock:
            self._target = target

    def snapshot(self) -> dict:
        with self._lock:
            data = dict(self._state)
            data["target"] = self._target
            return data

    def get_detections(self) -> List[Detection]:
        with self._lock:
            return list(self._detections)

    # ---------- worker ----------
    def _set_state(self, **kwargs) -> None:
        with self._lock:
            self._state = {**self._state, **kwargs}

    def _run(self) -> None:
        while not self._stop.is_set():
            if self._ocr.error:
                self._set_state(status="error", message=self._ocr.error)
                self._stop.wait(1.0)
                continue
            if not self._ocr.ready:
                self._set_state(status="loading",
                                message="Loading EasyOCR model (first run downloads it)…")
                self._stop.wait(0.5)
                continue
            frame = self._camera.get_frame()
            if frame is None:
                self._stop.wait(0.1)
                continue
            try:
                detections = self._ocr.read(frame)
                outcome = evaluate_frame(detections, self._catalog.names())
            except Exception as exc:  # noqa: BLE001
                self._set_state(status="error", message=f"OCR error: {exc}")
                self._stop.wait(1.0)
                continue
            self._process(detections, outcome)
            self._stop.wait(config.OCR_INTERVAL_SECONDS)

    def _process(self, detections: List[Detection], outcome: FrameOutcome) -> None:
        key = None
        if outcome.kind == "product":
            key = outcome.product
        elif outcome.kind == "unknown":
            key = _UNKNOWN

        with self._lock:
            self._detections = detections
            self._history.append(key)
            target = self._target
            votes = Counter(k for k in self._history if k is not None)

        texts = outcome.texts
        state: dict

        if votes and votes.most_common(1)[0][1] >= config.REQUIRED_AGREEMENT:
            winner = votes.most_common(1)[0][0]
            shown = "Unknown product" if winner == _UNKNOWN else winner
            passed = winner == target
            state = {
                "status": "pass" if passed else "reject",
                "detected_product": shown,
                "detected_texts": texts,
                "confidence": round(outcome.confidence, 2),
                "message": ("Label matches the selected bucket." if passed else
                            f"Label does not match '{target}'."),
            }
        elif outcome.kind == "unclear":
            state = {
                "status": "unclear",
                "detected_product": "",
                "detected_texts": texts,
                "confidence": round(outcome.confidence, 2),
                "message": "Text unclear. Move closer, reduce glare, hold steady.",
            }
        else:
            state = {
                "status": "scanning",
                "detected_product": "",
                "detected_texts": texts,
                "confidence": round(outcome.confidence, 2),
                "message": "Confirming…",
            }
        self._set_state(**state)