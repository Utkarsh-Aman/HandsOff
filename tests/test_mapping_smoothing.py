"""Tests for the other two pure pieces: coordinate mapping and smoothing."""

from handsoff.mapping import map_to_screen
from handsoff.smoothing import ExponentialSmoother


def test_frame_centre_maps_to_screen_centre():
    x, y = map_to_screen(0.5, 0.5, 1000, 500, margin=0.1)
    assert (x, y) == (499, 249)  # int() truncates 499.5 -> 499


def test_margin_edge_maps_to_screen_edge():
    assert map_to_screen(0.1, 0.1, 1000, 500, margin=0.1) == (0, 0)
    assert map_to_screen(0.9, 0.9, 1000, 500, margin=0.1) == (999, 499)


def test_outside_margin_is_clamped():
    assert map_to_screen(0.0, 1.0, 1000, 500, margin=0.1) == (0, 499)


def test_first_sample_passes_through_unchanged():
    s = ExponentialSmoother(alpha=0.5)
    assert s.update(0.3, 0.7) == (0.3, 0.7)


def test_smoother_moves_partway_toward_new_sample():
    s = ExponentialSmoother(alpha=0.5)
    s.update(0.0, 0.0)
    assert s.update(1.0, 1.0) == (0.5, 0.5)   # halfway with alpha 0.5
    assert s.update(1.0, 1.0) == (0.75, 0.75)  # keeps converging


def test_reset_forgets_history():
    s = ExponentialSmoother(alpha=0.5)
    s.update(0.0, 0.0)
    s.reset()
    assert s.update(1.0, 1.0) == (1.0, 1.0)
