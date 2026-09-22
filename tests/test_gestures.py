"""Unit tests for the pure gesture rules. No webcam or MediaPipe needed.

Each test builds a fake hand from 21 hand-picked coordinates and checks the
classifier's answer. Because classify() is a pure function, that is the whole
test: no mocking, no hardware.
"""

from handsoff.gestures import (
    INDEX_MCP,
    INDEX_PIP,
    INDEX_TIP,
    MIDDLE_PIP,
    MIDDLE_TIP,
    PINKY_PIP,
    PINKY_TIP,
    RING_PIP,
    RING_TIP,
    THUMB_TIP,
    WRIST,
    Gesture,
    classify,
)


def make_hand(*, index=False, middle=False, ring=False, pinky=False, pinch_with=None):
    """Build a synthetic upright hand as 21 (x, y) landmarks.

    Wrist sits at the bottom, index base 0.3 above it (palm length 0.3).
    Each finger's PIP joint is at y=0.5; its tip is above (0.3) when the finger
    is "up" or below (0.7) when curled. Landmarks we don't care about are left
    at the wrist position. `pinch_with` puts the thumb tip almost on top of
    the named fingertip index.
    """
    pts = [(0.5, 0.9)] * 21
    pts[WRIST] = (0.5, 0.9)
    pts[INDEX_MCP] = (0.5, 0.6)
    pts[THUMB_TIP] = (0.2, 0.7)  # far from every fingertip by default

    fingers = [
        (INDEX_TIP, INDEX_PIP, 0.50, index),
        (MIDDLE_TIP, MIDDLE_PIP, 0.55, middle),
        (RING_TIP, RING_PIP, 0.60, ring),
        (PINKY_TIP, PINKY_PIP, 0.65, pinky),
    ]
    for tip, pip, x, up in fingers:
        pts[pip] = (x, 0.5)
        pts[tip] = (x, 0.3 if up else 0.7)

    if pinch_with is not None:
        tx, ty = pts[pinch_with]
        pts[THUMB_TIP] = (tx + 0.02, ty)  # gap 0.02 / palm 0.3 = ratio 0.07, well under threshold
    return pts


def test_no_hand_is_none():
    assert classify(None) == Gesture.NONE


def test_index_only_is_point():
    assert classify(make_hand(index=True)) == Gesture.POINT


def test_index_and_middle_is_scroll():
    assert classify(make_hand(index=True, middle=True)) == Gesture.SCROLL


def test_fist_is_none():
    assert classify(make_hand()) == Gesture.NONE


def test_open_palm_is_none():
    assert classify(make_hand(index=True, middle=True, ring=True, pinky=True)) == Gesture.NONE


def test_thumb_touching_index_is_pinch():
    assert classify(make_hand(index=True, pinch_with=INDEX_TIP)) == Gesture.PINCH


def test_thumb_touching_middle_is_right_pinch():
    assert classify(make_hand(middle=True, pinch_with=MIDDLE_TIP)) == Gesture.RIGHT_PINCH


def test_pinch_wins_over_finger_pattern():
    # Index + middle up would be SCROLL, but a pinch is checked first.
    assert classify(make_hand(index=True, middle=True, pinch_with=INDEX_TIP)) == Gesture.PINCH


def test_pinch_is_scale_invariant():
    # Shrink the whole hand toward the wrist (hand further from the camera).
    # The thumb-index gap shrinks too, but so does the palm, so the ratio
    # and therefore the verdict must not change.
    hand = make_hand(index=True, pinch_with=INDEX_TIP)
    wx, wy = hand[WRIST]
    small = [(wx + (x - wx) * 0.4, wy + (y - wy) * 0.4) for x, y in hand]
    assert classify(small) == Gesture.PINCH
