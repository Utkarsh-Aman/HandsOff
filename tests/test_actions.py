"""Tests for the pose -> action mapper in both schemes.

The mapper takes the clock as an argument, so these tests fake time by
passing whatever `now` they like. No sleeping, no hardware.
"""

import pytest

from handsoff import config
from handsoff.actions import ActionMapper, Actions
from handsoff.gestures import Gesture


def frames(mapper, poses, dt=0.033):
    """Feed a list of poses one per frame (~30 fps) and return the Actions list."""
    return [mapper.update(p, i * dt) for i, p in enumerate(poses)]


def test_unknown_scheme_is_rejected():
    with pytest.raises(ValueError):
        ActionMapper("banana")


# --- pinch scheme ---------------------------------------------------------

def test_pinch_scheme_point_moves_only():
    m = ActionMapper("pinch")
    assert m.update(Gesture.POINT, 0.0) == Actions(move=True)


def test_pinch_scheme_pinch_moves_and_holds():
    m = ActionMapper("pinch")
    assert m.update(Gesture.PINCH, 0.0) == Actions(move=True, hold_left=True)


def test_pinch_scheme_right_click_fires_once_while_held():
    m = ActionMapper("pinch")
    out = frames(m, [Gesture.MIDDLE_PINCH] * 5)
    assert [a.right_click for a in out] == [True, False, False, False, False]


def test_pinch_scheme_fist_does_nothing():
    m = ActionMapper("pinch")
    assert m.update(Gesture.FIST, 0.0) == Actions()


# --- fist scheme ----------------------------------------------------------

def test_fist_scheme_fist_moves_and_holds():
    m = ActionMapper("fist")
    assert m.update(Gesture.FIST, 0.0) == Actions(move=True, hold_left=True)


def test_fist_scheme_pinch_does_nothing():
    m = ActionMapper("fist")
    assert m.update(Gesture.PINCH, 0.0) == Actions()


def test_two_quick_fists_right_click_on_the_second():
    m = ActionMapper("fist")
    m.update(Gesture.FIST, 0.0)
    m.update(Gesture.NONE, 0.2)          # open the hand
    second = m.update(Gesture.FIST, 0.4)  # well inside the window
    assert second.right_click is True


def test_two_slow_fists_do_not_right_click():
    m = ActionMapper("fist")
    m.update(Gesture.FIST, 0.0)
    m.update(Gesture.NONE, 0.5)
    late = m.update(Gesture.FIST, config.DOUBLE_FIST_WINDOW + 0.1)
    assert late.right_click is False


def test_third_fist_starts_a_fresh_pair():
    m = ActionMapper("fist")
    m.update(Gesture.FIST, 0.0)
    m.update(Gesture.NONE, 0.1)
    assert m.update(Gesture.FIST, 0.2).right_click is True
    m.update(Gesture.NONE, 0.3)
    assert m.update(Gesture.FIST, 0.4).right_click is False  # pair was consumed


def test_hand_down_pages_up_once():
    m = ActionMapper("fist")
    out = frames(m, [Gesture.HAND_DOWN] * 4)
    assert [a.page_up for a in out] == [True, False, False, False]


def test_middle_finger_quits_only_after_hold():
    m = ActionMapper("fist")
    assert m.update(Gesture.MIDDLE_FINGER, 0.0).quit is False
    assert m.update(Gesture.MIDDLE_FINGER, config.QUIT_HOLD_SECONDS - 0.1).quit is False
    assert m.update(Gesture.MIDDLE_FINGER, config.QUIT_HOLD_SECONDS).quit is True


def test_middle_finger_hold_resets_if_released():
    m = ActionMapper("fist")
    m.update(Gesture.MIDDLE_FINGER, 0.0)
    m.update(Gesture.NONE, 1.0)                # let go
    m.update(Gesture.MIDDLE_FINGER, 1.5)       # raise again: timer restarts here
    assert m.update(Gesture.MIDDLE_FINGER, 3.0).quit is False  # only 1.5 s into the new hold
