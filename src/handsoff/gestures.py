"""Rule-based gesture classification on hand landmarks.

Everything in this file is a *pure function*: landmarks in, answer out, no
camera, no OS calls, no state. That is what makes it easy to unit-test (see
tests/test_gestures.py) and easy to reason about.

The rules are deliberately simple geometry:
  * "finger is up"  = fingertip is above the finger's middle joint
  * "pinch"         = thumb tip is close to a fingertip, relative to palm size
"""

import math
from enum import Enum

from handsoff import config

# MediaPipe hand landmark indices (21 points). Each finger has four points
# from the base (MCP) to the tip. We only need a few of them.
WRIST = 0
THUMB_TIP = 4
INDEX_MCP, INDEX_PIP, INDEX_TIP = 5, 6, 8
MIDDLE_PIP, MIDDLE_TIP = 10, 12
RING_PIP, RING_TIP = 14, 16
PINKY_PIP, PINKY_TIP = 18, 20

Point = tuple[float, float]


class Gesture(Enum):
    """The handful of hand poses this controller understands."""

    NONE = "none"                # no hand, fist, or anything unrecognised -> do nothing
    POINT = "point"              # index finger up            -> move the cursor
    PINCH = "pinch"              # thumb + index touching     -> hold left button (click/drag)
    RIGHT_PINCH = "right_pinch"  # thumb + middle touching    -> right click
    SCROLL = "scroll"            # index + middle up (peace)  -> scroll with vertical motion


def distance(a: Point, b: Point) -> float:
    """Euclidean distance between two 2D points."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def finger_is_up(landmarks: list[Point], tip: int, pip: int) -> bool:
    """True if a finger is extended, judged by its tip being above its PIP joint.

    Image coordinates grow *downward*, so "above" means a smaller y. This rule
    assumes the hand is roughly upright (fingers pointing at the ceiling),
    which is the natural pose when pointing at a screen. A sideways hand
    would break it, but the simplicity is worth that limitation.
    """
    return landmarks[tip][1] < landmarks[pip][1]


def is_pinching(landmarks: list[Point], fingertip: int) -> bool:
    """True if the thumb tip is touching the given fingertip.

    The raw distance between the tips shrinks as the hand moves away from the
    camera, so a fixed threshold would fail at different distances. Dividing
    by the palm length (wrist to index base) makes the rule scale-invariant:
    the ratio is roughly the same at any distance.
    """
    palm_length = distance(landmarks[WRIST], landmarks[INDEX_MCP])
    if palm_length == 0:  # degenerate landmarks; avoid division by zero
        return False
    tip_gap = distance(landmarks[THUMB_TIP], landmarks[fingertip])
    return tip_gap / palm_length < config.PINCH_RATIO


def classify(landmarks: list[Point] | None) -> Gesture:
    """Map 21 landmarks to a Gesture using ordered geometric rules.

    Order matters. Pinches are checked first because while pinching, the
    index finger curls and may no longer count as "up", so a finger-count
    rule would misread it as NONE. The remaining rules are mutually exclusive
    finger-up patterns.
    """
    if landmarks is None:
        return Gesture.NONE

    if is_pinching(landmarks, INDEX_TIP):
        return Gesture.PINCH
    if is_pinching(landmarks, MIDDLE_TIP):
        return Gesture.RIGHT_PINCH

    index_up = finger_is_up(landmarks, INDEX_TIP, INDEX_PIP)
    middle_up = finger_is_up(landmarks, MIDDLE_TIP, MIDDLE_PIP)
    ring_up = finger_is_up(landmarks, RING_TIP, RING_PIP)
    pinky_up = finger_is_up(landmarks, PINKY_TIP, PINKY_PIP)

    if index_up and middle_up and not ring_up and not pinky_up:
        return Gesture.SCROLL
    if index_up and not middle_up and not ring_up and not pinky_up:
        return Gesture.POINT
    return Gesture.NONE
