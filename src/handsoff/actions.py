"""Turns a stream of hand poses into desktop actions, according to a scheme.

gestures.py answers "what shape is the hand?" one frame at a time. This
module answers "so what should happen?", which needs two more things:

  * a *scheme*: the user's chosen mapping from poses to actions
  * a little memory across frames, because some actions depend on time:
    a right click fires on the first frame of a pinch (not every frame it is
    held), a double fist needs the previous fist's timestamp, and the quit
    gesture must be held for a couple of seconds.

The clock is passed in (`now`) rather than read from time.monotonic() inside,
so the tests can fake the passage of time.
"""

from dataclasses import dataclass

from handsoff import config
from handsoff.gestures import INDEX_MCP, INDEX_TIP, Gesture

SCHEMES = ("pinch", "fist")

# Which landmark the cursor follows in each scheme. Pointing feels most
# natural from the fingertip. But in the fist scheme the fingertip drops a
# whole palm-length when you close your hand to click, which would throw the
# cursor off target; the index knuckle barely moves between point and fist.
CURSOR_LANDMARK = {"pinch": INDEX_TIP, "fist": INDEX_MCP}


@dataclass
class Actions:
    """What the OS layer should do this frame. All flags default to 'nothing'.

    Several can be true at once: a drag is `move` and `hold_left` together.
    """

    move: bool = False         # move the cursor to the tracked landmark
    hold_left: bool = False    # keep the left button down (level-triggered)
    right_click: bool = False  # send one right click (edge-triggered)
    scroll: bool = False       # scroll by this frame's vertical hand motion
    page_up: bool = False      # press the Page Up key once
    quit: bool = False         # exit the program


class ActionMapper:
    """Stateful pose -> Actions mapper for one scheme.

    Call update() once per frame with the classified pose and the current
    time. The only state kept is the previous pose (to detect transitions),
    the time the last fist began (double-fist detection) and the time the
    middle finger was raised (hold-to-quit).
    """

    def __init__(self, scheme: str) -> None:
        if scheme not in SCHEMES:
            raise ValueError(f"unknown scheme {scheme!r}; choose from {SCHEMES}")
        self.scheme = scheme
        self.cursor_landmark = CURSOR_LANDMARK[scheme]
        self._prev = Gesture.NONE
        self._last_fist_start: float | None = None
        self._middle_start: float | None = None

    def update(self, gesture: Gesture, now: float) -> Actions:
        """Return the actions for this frame and remember the pose for next time.

        `started` is true on the first frame of a new pose. Edge-triggered
        actions (right click, page up) use it so they fire once per gesture
        rather than once per frame.
        """
        started = gesture != self._prev
        if self.scheme == "pinch":
            actions = self._pinch_scheme(gesture, started)
        else:
            actions = self._fist_scheme(gesture, started, now)
        self._prev = gesture
        return actions

    @staticmethod
    def _pinch_scheme(g: Gesture, started: bool) -> Actions:
        """Scheme 'pinch': thumb-to-finger pinches do the clicking.

        POINT / PINCH  -> move (moving while pinching gives drag-and-drop)
        PINCH          -> hold left button
        MIDDLE_PINCH   -> right click, once
        SCROLL         -> scroll
        """
        return Actions(
            move=g in (Gesture.POINT, Gesture.PINCH),
            hold_left=g == Gesture.PINCH,
            right_click=g == Gesture.MIDDLE_PINCH and started,
            scroll=g == Gesture.SCROLL,
        )

    def _fist_scheme(self, g: Gesture, started: bool, now: float) -> Actions:
        """Scheme 'fist': closing the hand does the clicking.

        POINT / FIST   -> move (moving with a closed fist gives drag-and-drop)
        FIST           -> hold left button; tap = click, hold = drag
        FIST twice     -> right click (two fists starting within DOUBLE_FIST_WINDOW)
        SCROLL         -> scroll
        HAND_DOWN      -> Page Up, once per dip
        MIDDLE_FINGER  -> quit after QUIT_HOLD_SECONDS

        Note the double fist also produces two left clicks on the way, exactly
        like a mouse double-click does. Suppressing them would mean delaying
        every single click by the window length, which feels sluggish.
        """
        actions = Actions(
            move=g in (Gesture.POINT, Gesture.FIST),
            hold_left=g == Gesture.FIST,
            scroll=g == Gesture.SCROLL,
            page_up=g == Gesture.HAND_DOWN and started,
        )

        if g == Gesture.FIST and started:
            recent = self._last_fist_start is not None and now - self._last_fist_start < config.DOUBLE_FIST_WINDOW
            if recent:
                actions.right_click = True
                self._last_fist_start = None  # consumed: a third fist starts a fresh pair
            else:
                self._last_fist_start = now

        if g == Gesture.MIDDLE_FINGER:
            if started:
                self._middle_start = now
            elif now - self._middle_start >= config.QUIT_HOLD_SECONDS:
                actions.quit = True

        return actions
