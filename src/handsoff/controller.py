"""The only module that touches the operating system (via pyautogui).

Everything else in the project *decides* what should happen; this class
*does* it. Keeping side effects in one place means the rest of the code can
be tested and reasoned about without a real mouse moving around.
"""

import pyautogui

# pyautogui sleeps 0.1 s after EVERY call by default. At ~30 frames/second
# that would make the cursor crawl, so switch the pause off.
pyautogui.PAUSE = 0

# The fail-safe aborts the program if the cursor hits a screen corner. Our
# cursor is *supposed* to reach the corners, so it would trigger constantly.
# Quit with the 'q' key or Ctrl+C instead.
pyautogui.FAILSAFE = False


class DesktopController:
    """Moves the cursor, presses buttons and scrolls."""

    def __init__(self) -> None:
        self.screen_w, self.screen_h = pyautogui.size()
        self._left_down = False  # remembered so we only send real transitions

    def move_to(self, x: int, y: int) -> None:
        """Move the cursor to absolute screen pixel (x, y)."""
        pyautogui.moveTo(x, y)

    def set_left_button(self, down: bool) -> None:
        """Hold or release the left mouse button, sending only state *changes*.

        Called every frame with "is the user pinching right now?". A short
        pinch produces press + release = a click; a long pinch while moving
        the hand produces a drag. Neither needs a timer or a cooldown, and the
        OS never receives a redundant press while the button is already down.
        """
        if down and not self._left_down:
            pyautogui.mouseDown()
        elif not down and self._left_down:
            pyautogui.mouseUp()
        self._left_down = down

    def right_click(self) -> None:
        """Send a single right click."""
        pyautogui.click(button="right")

    def scroll(self, clicks: int) -> None:
        """Scroll the wheel by `clicks` notches. Positive = up, negative = down."""
        if clicks != 0:
            pyautogui.scroll(clicks)

    def release_all(self) -> None:
        """Make sure no button is left held down when the program exits."""
        self.set_left_button(False)
