"""Unit tests for the pure pose rules. No webcam or MediaPipe needed.

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

    Wrist sits at the bottom, index knuckle 0.3 above it (palm length 0.3).
    Each finger's PIP joint is at y=0.5; its tip is above (0.3) when the finger
    is "up" or curled back near the wrist (0.75) when down, which also keeps
    it inside the fist radius. Landmarks we don't care about are left at the
    wrist position. `pinch_with` puts the thumb tip almost on top of the named
    fingertip index.
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
        pts[tip] = (x, 0.3 if up else 0.75)

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


def test_middle_only_is_middle_finger():
    assert classify(make_hand(middle=True)) == Gesture.MIDDLE_FINGER


def test_all_fingers_curled_is_fist():
    assert classify(make_hand()) == Gesture.FIST


def test_open_palm_is_none():
    assert classify(make_hand(index=True, middle=True, ring=True, pinky=True)) == Gesture.NONE


def test_thumb_touching_index_is_pinch():
    assert classify(make_hand(index=True, pinch_with=INDEX_TIP)) == Gesture.PINCH


def test_thumb_touching_middle_is_middle_pinch():
    assert classify(make_hand(middle=True, pinch_with=MIDDLE_TIP)) == Gesture.MIDDLE_PINCH


def test_pinch_wins_over_finger_pattern():
    # Index + middle up would be SCROLL, but a pinch is checked first.
    assert classify(make_hand(index=True, middle=True, pinch_with=INDEX_TIP)) == Gesture.PINCH


def test_fist_wins_over_pinch():
    # In a real fist the thumb often rests on the curled index finger, which
    # the pinch rule alone would misread. The fist rule is checked first.
    hand = make_hand()
    hand[THUMB_TIP] = hand[INDEX_TIP]
    assert classify(hand) == Gesture.FIST


def test_fingers_below_wrist_is_hand_down():
    hand = make_hand(index=True, middle=True, ring=True, pinky=True)
    # Flip the hand: put every fingertip and joint *below* the wrist.
    hand = [(x, 1.8 - y) if i != WRIST else (x, y) for i, (x, y) in enumerate(hand)]
    assert classify(hand) == Gesture.HAND_DOWN


def test_pinch_is_scale_invariant():
    # Shrink the whole hand toward the wrist (hand further from the camera).
    # The thumb-index gap shrinks too, but so does the palm, so the ratio
    # and therefore the verdict must not change.
    hand = make_hand(index=True, pinch_with=INDEX_TIP)
    wx, wy = hand[WRIST]
    small = [(wx + (x - wx) * 0.4, wy + (y - wy) * 0.4) for x, y in hand]
    assert classify(small) == Gesture.PINCH
