# HandsOff

Control your desktop cursor with hand gestures from a webcam. 
project: MediaPipe finds the hand, a few geometric rules turn landmarks into gestures, and pyautogui drives the mouse.


## Gestures

Five gestures are registered. The name in the left column is what the
preview window prints while the gesture is active, so you can check what the
rules are seeing.

| Name          | How to do it                                                | What happens                                   |
| ------------- | ----------------------------------------------------------- | ---------------------------------------------- |
| `point`       | Raise only your index finger, curl the other three.         | The cursor follows your index fingertip.       |
| `pinch`       | Touch thumb tip to index fingertip.                         | Left button is held. Tap = click. Hold and move = drag. Release to let go. |
| `right_pinch` | Touch thumb tip to **middle** fingertip.                    | One right click, fired the moment the pinch starts. |
| `scroll`      | Raise index and middle fingers ("peace" sign), then move the hand up or down. | Page scrolls in the direction your hand moves. Cursor stays put. |
| `none`        | Fist, open palm, hand out of view, or anything unrecognised. | Nothing. Use this to rest without moving the cursor. |

### Tips for reliable recognition

- Keep your hand roughly upright, fingers toward the ceiling, palm facing the
  camera. The "finger up" rule compares fingertip height to the knuckle, so a
  sideways hand confuses it.
- Only the central part of the camera view is mapped to the screen, so small
  hand movements are enough to cross the whole display.
- To click without the cursor drifting, stop moving first, then pinch.
- Start from `none` (open palm or fist) before switching between `pinch` and
  `right_pinch`, otherwise the rules can briefly read the transition as the
  other pinch.
- The `pinch` gesture is checked before the finger-count gestures, so you
  can pinch while other fingers are in any position.

All thresholds that decide these gestures are in
[src/handsoff/config.py](src/handsoff/config.py), and the rules themselves
are in [src/handsoff/gestures.py](src/handsoff/gestures.py).

## Setup

### With uv (recommended)

Requires [uv](https://docs.astral.sh/uv/). It will fetch Python 3.11 for you
if the machine doesn't have it.

```bash
git clone https://github.com/Utkarsh-Aman/HandsOff
cd HandsOff
uv sync
```

That creates `.venv/` and installs the exact versions pinned in `uv.lock`.

### Without uv (plain pip)

`pyproject.toml` is a standard packaging file, so pip works too. You need
Python 3.11 or newer already installed.

```bash
git clone https://github.com/Utkarsh-Aman/HandsOff
cd HandsOff
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux
pip install -e .
```

`pip install -e .` reads the dependencies from `pyproject.toml` and creates
the `handsoff` command. Differences from the uv route:

- pip ignores `uv.lock`, so you get the newest versions that satisfy the
  ranges in `pyproject.toml` rather than the exact pinned ones.
- pytest is not installed. Add it with `pip install pytest` if you want to
  run the tests.

### The model file

The MediaPipe hand model (~8 MB) is not in the repository. It is downloaded
automatically into `models/` the first time you run the app, so that first
run needs an internet connection. After that it is cached locally.

## Run

```bash
uv run handsoff
```

Or, if you installed with pip and the venv is activated, just `handsoff`.

A preview window shows the webcam feed with landmarks and the current gesture
name. Press `q` in that window (or Ctrl+C in the terminal) to quit.

## Test

```bash
uv run pytest
```

The tests cover only the pure logic (gesture rules, coordinate mapping,
smoothing) and need no webcam.

## Tuning

Every threshold lives in [src/handsoff/config.py](src/handsoff/config.py):

- Cursor shaky? Lower `SMOOTHING_ALPHA`. Cursor laggy? Raise it.
- Clicks not registering? Raise `PINCH_RATIO`. Ghost clicks? Lower it.
- Can't reach the screen edge? Raise `FRAME_MARGIN`.
- Wrong camera? Change `CAMERA_INDEX`.

## Learning path

See [master.md](master.md) for a guided, file-by-file tour of the code.
