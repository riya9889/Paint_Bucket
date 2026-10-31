"""Threaded OpenCV webcam reader that always keeps the newest frame."""
import os
import threading
from typing import Optional

import cv2
import numpy as np


class Camera:
    def __init__(self, index: int = 0, width: int = 1280, height: int = 720):
        self._index = index
        self._width = width
        self._height = height
        self._cap: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._frame: Optional[np.ndarray] = None
        self.last_error = ""

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _open(self) -> Optional[cv2.VideoCapture]:
        backends = [cv2.CAP_DSHOW, cv2.CAP_ANY] if os.name == "nt" else [cv2.CAP_ANY]
        for backend in backends:
            cap = cv2.VideoCapture(self._index, backend)
            if cap.isOpened():
                return cap
            cap.release()
        return None

    def start(self) -> bool:
        if self.is_running:
            return True
        cap = self._open()
        if cap is None:
            self.last_error = (
                "Could not open the webcam. Close other apps using it "
                "(Teams, Zoom, Camera) and check Windows camera privacy settings."
            )
            return False
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
        self._cap = cap
        self._frame = None
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self.last_error = ""
        return True

    def _loop(self) -> None:
        while not self._stop.is_set():
            ok, frame = self._cap.read()
            if not ok or frame is None:
                self._stop.wait(0.05)
                continue
            with self._lock:
                self._frame = frame

    def get_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            return None if self._frame is None else self._frame.copy()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        with self._lock:
            self._frame = None