"""Coordinate transform: normalised camera position -> screen pixel.

Another pure function, kept separate from the OS layer so it can be tested
without a screen and tweaked without touching pyautogui.
"""

from handsoff import config


def map_to_screen(
    nx: float,
    ny: float,
    screen_w: int,
    screen_h: int,
    margin: float = config.FRAME_MARGIN,
) -> tuple[int, int]:
    """Convert a landmark's (x, y) in [0, 1] frame space to a screen pixel.

    The frame is assumed to be already mirrored (see main.py), so x increases
    to the right just like on the screen. Only the inner region
    [margin, 1 - margin] of the frame is used: it is rescaled to cover the
    whole screen, so a modest hand movement reaches every screen edge and you
    never have to hold your hand at the border of the camera's view.

    The result is clamped so the cursor can't be asked to go off-screen.
    """
    usable = 1.0 - 2 * margin  # width of the inner region, in frame units

    # Shift so the inner region starts at 0, then stretch it to [0, 1].
    sx = (nx - margin) / usable
    sy = (ny - margin) / usable

    # Clamp to [0, 1] then scale to pixels. `screen_w - 1` because pixel
    # coordinates run from 0 to width-1 inclusive.
    sx = min(max(sx, 0.0), 1.0)
    sy = min(max(sy, 0.0), 1.0)
    return int(sx * (screen_w - 1)), int(sy * (screen_h - 1))
