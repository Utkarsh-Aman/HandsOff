"""Cursor smoothing with an exponential moving average (EMA).

Hand landmarks jitter by a few pixels every frame even when the hand is
perfectly still. Sent straight to the OS, that jitter becomes a shaky cursor.
An EMA blends each new reading with the previous smoothed value, so noise is
averaged away while genuine movement still comes through.
"""

from handsoff import config


class ExponentialSmoother:
    """Smooths a stream of 2D points.

    smoothed = alpha * new + (1 - alpha) * previous_smoothed

    alpha controls the trade-off: high alpha follows the hand quickly but
    keeps more jitter; low alpha is silky-smooth but lags behind fast moves.
    """

    def __init__(self, alpha: float = config.SMOOTHING_ALPHA) -> None:
        self.alpha = alpha
        self._prev: tuple[float, float] | None = None

    def update(self, x: float, y: float) -> tuple[float, float]:
        """Feed in a new raw point and get back the smoothed point.

        The very first point is returned as-is; there is nothing to blend it
        with, and starting from (0, 0) would make the cursor visibly "fly in"
        from the corner.
        """
        if self._prev is None:
            self._prev = (x, y)
            return self._prev
        px, py = self._prev
        a = self.alpha
        self._prev = (a * x + (1 - a) * px, a * y + (1 - a) * py)
        return self._prev

    def reset(self) -> None:
        """Forget the history, e.g. when the hand leaves the frame.

        Without this, when the hand reappears somewhere else the cursor would
        slowly glide from its old position instead of jumping to the new one.
        """
        self._prev = None
