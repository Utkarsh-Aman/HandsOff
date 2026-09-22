"""Entry point: the capture -> track -> classify -> act loop.

This file wires the other modules together and nothing more. Read it top to
bottom and you should see the whole pipeline: grab a frame, find the hand,
decide the gesture, smooth the position, and hand the result to the OS.
"""

import cv2

from handsoff import config
from handsoff.controller import DesktopController
from handsoff.gestures import INDEX_TIP, Gesture, classify
from handsoff.mapping import map_to_screen
from handsoff.smoothing import ExponentialSmoother
from handsoff.tracker import HandTracker


def draw_debug(frame, landmarks, gesture: Gesture) -> None:
    """Draw landmarks and the current gesture name onto the preview frame.

    Purely for feedback while learning/tuning: seeing where MediaPipe thinks
    your fingertips are makes it obvious why a gesture did or didn't fire.
    """
    h, w = frame.shape[:2]
    if landmarks:
        for x, y in landmarks:
            # Landmarks are normalised [0, 1]; scale back to pixels to draw.
            cv2.circle(frame, (int(x * w), int(y * h)), 4, (0, 255, 0), -1)
    cv2.putText(frame, gesture.value, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)


def run(cap, tracker: HandTracker, smoother: ExponentialSmoother, controller: DesktopController) -> None:
    """Process frames until the user quits ('q' in the preview or Ctrl+C).

    Two pieces of state carry over between frames:
      * prev_gesture - so we can react to *transitions* (e.g. right-click once
        when the pinch starts, not 30 times a second while it is held)
      * prev_y       - the previous smoothed fingertip height, so scrolling
        can be driven by how far the hand moved since the last frame
    """
    prev_gesture = Gesture.NONE
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

        if landmarks is None:
            # Hand left the frame: forget smoothing history so the cursor
            # jumps (not glides) to wherever the hand reappears.
            smoother.reset()
            prev_y = None
        else:
            # Always feed the smoother while a hand is visible, even for
            # gestures that don't move the cursor. Otherwise its memory goes
            # stale during a scroll and the cursor lurches when pointing resumes.
            raw_x, raw_y = landmarks[INDEX_TIP]
            x, y = smoother.update(raw_x, raw_y)

            if gesture in (Gesture.POINT, Gesture.PINCH):
                # Moving while pinching is what makes drag-and-drop work.
                controller.move_to(*map_to_screen(x, y, controller.screen_w, controller.screen_h))

            if gesture == Gesture.SCROLL and prev_gesture == Gesture.SCROLL and prev_y is not None:
                # Image y grows downward, so moving the hand *up* makes
                # (prev_y - y) positive, which pyautogui treats as scroll up.
                controller.scroll(round((prev_y - y) * config.SCROLL_SPEED))
            prev_y = y

        # Button state is level-triggered: held while pinching, released otherwise.
        controller.set_left_button(gesture == Gesture.PINCH)

        # Right click is edge-triggered: fire once on the frame the pinch begins.
        if gesture == Gesture.RIGHT_PINCH and prev_gesture != Gesture.RIGHT_PINCH:
            controller.right_click()

        prev_gesture = gesture

        if config.SHOW_PREVIEW:
            draw_debug(frame, landmarks, gesture)
            cv2.imshow("HandsOff (press q to quit)", frame)
            # waitKey also pumps the GUI event loop; without it the window never updates.
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break


def main() -> None:
    """Open the webcam, build the pipeline objects, run, and clean up."""
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    if not cap.isOpened():
        raise SystemExit(f"Could not open webcam {config.CAMERA_INDEX}. Try another CAMERA_INDEX in config.py.")

    tracker = HandTracker()
    smoother = ExponentialSmoother()
    controller = DesktopController()

    print("HandsOff running. Point to move, pinch to click, 'q' in the preview window or Ctrl+C to quit.")
    try:
        run(cap, tracker, smoother, controller)
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
