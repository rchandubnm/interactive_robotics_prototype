"""Thread-safe latest-frame buffer for WebRTC; no Streamlit access in callbacks."""
from __future__ import annotations
from threading import Lock
from PIL import Image
import numpy as np


class LatestFrame:
    def __init__(self, max_width: int = 960, keep_every: int = 5):
        self.lock = Lock()
        self._image = None
        self._sequence = 0
        self._count = 0
        self.max_width = max_width
        self.keep_every = max(1, keep_every)

    def on_frame(self, frame):
        """WebRTC callback invoked in an aiortc thread; return video unchanged."""
        with self.lock:
            self._count += 1
            should_save = self._count % self.keep_every == 0
        if should_save:
            arr = frame.to_ndarray(format='rgb24')
            h, w = arr.shape[:2]
            if w > self.max_width:
                from cv2 import resize, INTER_AREA
                arr = resize(arr, (self.max_width, int(h * self.max_width / w)), interpolation=INTER_AREA)
            im = Image.fromarray(np.asarray(arr, dtype=np.uint8))
            self.store(im)
        return frame

    def store(self, image: Image.Image):
        with self.lock:
            self._image = image.copy()
            self._sequence += 1

    def snapshot(self):
        with self.lock:
            if self._image is None:
                return None
            return self._sequence, self._image.copy()
