"""Entry point: the capture -> track -> classify -> map -> act loop.

This file wires the other modules together and nothing more. Read it top to
bottom and you should see the whole pipeline: grab a frame, find the hand,
decide the pose, turn the pose into actions for the chosen scheme, smooth
the position, and hand the result to the OS.
"""

import argparse
import time

import cv2

from handsoff import config
from handsoff.actions import SCHEMES, ActionMapper
from handsoff.controller import DesktopController
from handsoff.gestures import Gesture, classify
from handsoff.mapping import map_to_screen
from handsoff.smoothing import ExponentialSmoother
from handsoff.tracker import HandTracker


def draw_debug(frame, landmarks, gesture: Gesture, scheme: str) -> None:
    """Draw landmarks, the current pose and the active scheme onto the preview.

    Purely for feedback while learning/tuning: seeing where MediaPipe thinks
    your fingertips are makes it obvious why a pose did or didn't fire.
    """
    h, w = frame.shape[:2]
    if landmarks:
        for x, y in landmarks:
            # Landmarks are normalised [0, 1]; scale back to pixels to draw.
            cv2.circle(frame, (int(x * w), int(y * h)), 4, (0, 255, 0), -1)
    cv2.putText(frame, gesture.value, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    cv2.putText(frame, f"scheme: {scheme}", (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)


def run(cap, tracker: HandTracker, mapper: ActionMapper, smoother: ExponentialSmoother, controller: DesktopController) -> None:
    """Process frames until the user quits ('q' in the preview, Ctrl+C, or the quit gesture).

    The mapper remembers the previous pose and any timers, so the only state
    this loop keeps is `prev_y`: the previous smoothed hand height, used to
    turn vertical motion into scroll notches.
    """
    prev_y = None

    while True:
        ok, frame = cap.read()
        if not ok:
            print("Webcam frame not received; stopping.")
            break

        # Mirror the image so moving your hand right moves the cursor right.
        # Without this the webcam acts like a camera pointed at you, not a mirror.
        frame = cv2.flip(frame, 1)

        landmarks = tracker.detect(frame)
        gesture = classify(landmarks)
        actions = mapper.update(gesture, time.monotonic())

        if landmarks is None:
            # Hand left the frame: forget smoothing history so the cursor
            # jumps (not glides) to wherever the hand reappears.
            smoother.reset()
            prev_y = None
        else:
            # Always feed the smoother while a hand is visible, even for
            # poses that don't move the cursor. Otherwise its memory goes
            # stale during a scroll and the cursor lurches when pointing resumes.
            raw_x, raw_y = landmarks[mapper.cursor_landmark]
            x, y = smoother.update(raw_x, raw_y)

            if actions.move:
                controller.move_to(*map_to_screen(x, y, controller.screen_w, controller.screen_h))

            if actions.scroll and prev_y is not None:
                # Image y grows downward, so moving the hand *up* makes
                # (prev_y - y) positive, which pyautogui treats as scroll up.
                controller.scroll(round((prev_y - y) * config.SCROLL_SPEED))
            # Only carry a height over while scrolling, so the first scroll
            # frame after pointing doesn't produce a big jump.
            prev_y = y if actions.scroll else None

        # Level-triggered: held while the click pose is held, released otherwise.
        controller.set_left_button(actions.hold_left)

        # Edge-triggered: the mapper sets these on one frame only.
        if actions.right_click:
            controller.right_click()
        if actions.page_up:
            controller.page_up()
        if actions.quit:
            print("Quit gesture held; exiting.")
            break

        if config.SHOW_PREVIEW:
            draw_debug(frame, landmarks, gesture, mapper.scheme)
            cv2.imshow("HandsOff (press q to quit)", frame)
            # waitKey also pumps the GUI event loop; without it the window never updates.
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break


def parse_args() -> argparse.Namespace:
    """Read the one command-line option: which control scheme to use.

    The default comes from config.py so you can set your favourite once and
    still switch for a single run with `--scheme`.
    """
    parser = argparse.ArgumentParser(description="Control the desktop with hand gestures.")
    parser.add_argument("--scheme", choices=SCHEMES, default=config.SCHEME, help="which poses do the clicking")
    return parser.parse_args()


def main() -> None:
    """Open the webcam, build the pipeline objects, run, and clean up."""
    args = parse_args()

    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    if not cap.isOpened():
        raise SystemExit(f"Could not open webcam {config.CAMERA_INDEX}. Try another CAMERA_INDEX in config.py.")

    tracker = HandTracker()
    mapper = ActionMapper(args.scheme)
    smoother = ExponentialSmoother()
    controller = DesktopController()

    print(f"HandsOff running with the '{args.scheme}' scheme. Press 'q' in the preview window or Ctrl+C to quit.")
    try:
        run(cap, tracker, mapper, smoother, controller)
    except KeyboardInterrupt:
        pass
    finally:
        # Never leave the mouse button stuck down, whatever caused the exit.
        controller.release_all()
        tracker.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
