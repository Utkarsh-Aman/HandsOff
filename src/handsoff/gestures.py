"""Rule-based hand *pose* classification on hand landmarks.

Everything in this file is a *pure function*: landmarks in, answer out, no
camera, no OS calls, no state. That is what makes it easy to unit-test (see
tests/test_gestures.py) and easy to reason about.

This file only answers "what shape is the hand in?". What that shape should
*do* (click, scroll, quit) is decided separately in actions.py, so the same
classifier serves both control schemes.

The rules are deliberately simple geometry:
  * "finger is up"  = fingertip is above the finger's middle joint
  * "pinch"         = thumb tip is close to a fingertip, relative to palm size
  * "fist"          = all fingertips are close to the wrist, relative to palm size
  * "hand down"     = fingertips are below the wrist
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

FINGERTIPS = (INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP)

Point = tuple[float, float]


class Gesture(Enum):
    """The hand poses this project can recognise.

    These are *shapes*, not actions. See actions.py for what each one does in
    each control scheme.
    """

    NONE = "none"                  # no hand, open palm, or anything unrecognised
    POINT = "point"                # index finger up, others curled
    PINCH = "pinch"                # thumb tip touching index tip
    MIDDLE_PINCH = "middle_pinch"  # thumb tip touching middle tip
    SCROLL = "scroll"              # index + middle up ("peace" sign)
    FIST = "fist"                  # all fingers curled into the palm
    MIDDLE_FINGER = "middle"       # middle finger up, others curled
    HAND_DOWN = "hand_down"        # fingers pointing at the floor


def distance(a: Point, b: Point) -> float:
    """Euclidean distance between two 2D points."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def palm_length(landmarks: list[Point]) -> float:
    """Wrist-to-index-knuckle distance, used as the hand's size unit.

    Every distance-based rule divides by this so the rule gives the same
    answer whether the hand is close to the camera (big in the frame) or far
    away (small in the frame).
    """
    return distance(landmarks[WRIST], landmarks[INDEX_MCP])


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
    by the palm length makes the rule scale-invariant.
    """
    palm = palm_length(landmarks)
    if palm == 0:  # degenerate landmarks; avoid division by zero
        return False
    tip_gap = distance(landmarks[THUMB_TIP], landmarks[fingertip])
    return tip_gap / palm < config.PINCH_RATIO


def is_fist(landmarks: list[Point]) -> bool:
    """True if all four fingertips are curled in close to the wrist.

    We measure tip-to-wrist distance rather than using finger_is_up() because
    a pinching index finger also fails the "up" test but is still far from
    the wrist. Curled fingertips sit roughly at the palm's centre, i.e. well
    under one palm length from the wrist; extended ones are ~1.5 palm lengths
    away, so the two cases are easy to separate.
    """
    palm = palm_length(landmarks)
    if palm == 0:
        return False
    return all(distance(landmarks[WRIST], landmarks[t]) / palm < config.FIST_RATIO for t in FINGERTIPS)


def is_hand_down(landmarks: list[Point]) -> bool:
    """True if the hand is pointing at the floor.

    In an upright hand every fingertip is above the wrist. If the index and
    middle tips are *below* the wrist (larger y) the hand has been flipped
    over. Two fingers are checked rather than one so a single stray landmark
    can't trigger it.
    """
    wrist_y = landmarks[WRIST][1]
    return landmarks[INDEX_TIP][1] > wrist_y and landmarks[MIDDLE_TIP][1] > wrist_y


def classify(landmarks: list[Point] | None) -> Gesture:
    """Map 21 landmarks to a Gesture using ordered geometric rules.

    Order matters, and each placement has a reason:
      1. HAND_DOWN first: an inverted hand fails every "finger up" test and
         would otherwise be misread as a fist or as nothing.
      2. FIST before PINCH: in a fist the thumb often rests near the index
         tip, which looks like a pinch to the distance rule.
      3. PINCH before the finger-count rules: a pinching index finger curls
         and may no longer count as "up".
      4. The remaining rules are mutually exclusive finger-up patterns.
    """
    if landmarks is None:
        return Gesture.NONE

    if is_hand_down(landmarks):
        return Gesture.HAND_DOWN
    if is_fist(landmarks):
        return Gesture.FIST
    if is_pinching(landmarks, INDEX_TIP):
        return Gesture.PINCH
    if is_pinching(landmarks, MIDDLE_TIP):
        return Gesture.MIDDLE_PINCH

    index_up = finger_is_up(landmarks, INDEX_TIP, INDEX_PIP)
    middle_up = finger_is_up(landmarks, MIDDLE_TIP, MIDDLE_PIP)
    ring_up = finger_is_up(landmarks, RING_TIP, RING_PIP)
    pinky_up = finger_is_up(landmarks, PINKY_TIP, PINKY_PIP)

    if index_up and middle_up and not ring_up and not pinky_up:
        return Gesture.SCROLL
    if index_up and not middle_up and not ring_up and not pinky_up:
        return Gesture.POINT
    if middle_up and not index_up and not ring_up and not pinky_up:
        return Gesture.MIDDLE_FINGER
    return Gesture.NONE
