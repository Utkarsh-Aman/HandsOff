"""Thin wrapper around MediaPipe's hand landmark model.

The rest of the project never touches MediaPipe directly. It only sees this
class, which takes a BGR frame from OpenCV and returns a plain list of 21
(x, y) tuples (or None). That isolation matters: MediaPipe's API has changed
several times, and when it changes again only this file has to be updated.
"""

import time
import urllib.request

import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

from handsoff import config


def ensure_model_downloaded() -> None:
    """Download the hand landmark model file if it isn't on disk yet.

    MediaPipe's Tasks API loads a .task model file at startup. We fetch it on
    first run instead of committing it so the repository stays small.
    """
    if config.MODEL_PATH.exists():
        return
    print(f"Downloading hand landmark model to {config.MODEL_PATH} ...")
    config.MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(config.MODEL_URL, config.MODEL_PATH)
    print("Done.")


class HandTracker:
    """Detects one hand per frame and returns its 21 landmarks.

    Each landmark is a normalised (x, y) pair: x and y are in [0, 1] as a
    fraction of frame width/height, with (0, 0) at the top-left. We drop the z
    coordinate because every gesture rule in this project works in 2D.
    """

    def __init__(self) -> None:
        """Load the model in VIDEO mode.

        VIDEO mode (as opposed to IMAGE mode) lets MediaPipe reuse the previous
        frame's result to track the hand, which is faster and less jittery than
        detecting from scratch every frame.
        """
        ensure_model_downloaded()
        options = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(config.MODEL_PATH)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=1,  # one hand keeps the gesture logic simple and unambiguous
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)
        self._start_time = time.monotonic()

    def detect(self, frame_bgr) -> list[tuple[float, float]] | None:
        """Return the 21 (x, y) landmarks of the first detected hand, or None.

        OpenCV gives us BGR pixels; MediaPipe expects RGB, so the channels are
        reversed with a NumPy slice (`[..., ::-1]`) before wrapping the array in
        a MediaPipe Image. VIDEO mode also requires a monotonically increasing
        timestamp in milliseconds so it can order frames.
        """
        rgb = frame_bgr[..., ::-1].copy()
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        timestamp_ms = int((time.monotonic() - self._start_time) * 1000)

        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)
        if not result.hand_landmarks:
            return None
        hand = result.hand_landmarks[0]
        return [(lm.x, lm.y) for lm in hand]

    def close(self) -> None:
        """Release the model's native resources when the program exits."""
        self._landmarker.close()
