"""All tunable numbers in one place.

Keeping thresholds here (instead of scattered through the code) means that
when the controller feels wrong -- too jittery, clicks not registering,
can't reach the screen edge -- you know exactly where to look, and the
modules that use these values stay free of "magic numbers".
"""

from pathlib import Path

# --- Webcam ---------------------------------------------------------------
CAMERA_INDEX = 0            # 0 = the default/built-in camera; try 1 for an external one
FRAME_WIDTH = 640           # lower resolution = faster hand detection; we don't
FRAME_HEIGHT = 480          # need detail, just landmark positions

# --- Hand landmark model --------------------------------------------------
# MediaPipe's Tasks API needs a model file on disk. We download it once into
# models/ (git-ignored) rather than committing an ~8 MB binary.
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "hand_landmarker.task"

# --- Control scheme -------------------------------------------------------
# Which poses do the clicking. Override per run with `uv run handsoff --scheme fist`.
#   "pinch": thumb+index pinch = left button, thumb+middle pinch = right click
#   "fist":  fist = left button, two quick fists = right click,
#            hand pointing down = Page Up, middle finger held 2 s = quit
SCHEME = "pinch"

# --- Gesture thresholds ---------------------------------------------------
# Distances are measured relative to palm size (wrist to index knuckle) so
# the rules work whether the hand is near or far from the camera.
PINCH_RATIO = 0.35          # thumb-to-fingertip gap, as a fraction of palm length;
                            # lower = must pinch tighter
FIST_RATIO = 1.0            # every fingertip must be within this many palm lengths
                            # of the wrist to count as a fist; extended fingers are ~1.5

# --- Timing (seconds) -----------------------------------------------------
DOUBLE_FIST_WINDOW = 1.0    # two fists must *start* within this gap to be a right click
QUIT_HOLD_SECONDS = 2.0     # how long the middle finger must stay raised to quit

# --- Cursor mapping and smoothing ----------------------------------------
# Only the central part of the camera frame is mapped to the screen. Without
# this margin you'd have to move your hand to the very edge of the camera's
# view (where tracking is worst) to reach the screen edge.
FRAME_MARGIN = 0.15         # fraction of frame width/height to ignore on each side

# Exponential moving average factor, 0 < alpha <= 1.
#   alpha = 1.0 -> no smoothing (raw, jittery)
#   alpha = 0.1 -> very smooth but laggy
SMOOTHING_ALPHA = 0.35

# --- Scrolling ------------------------------------------------------------
# How many scroll "clicks" a full-frame-height vertical hand movement produces.
SCROLL_SPEED = 150

# --- Debug preview --------------------------------------------------------
SHOW_PREVIEW = True         # show the webcam window with landmarks drawn on it
