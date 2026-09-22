# HandsOff

Control your desktop cursor with hand gestures from a webcam. 
project: MediaPipe finds the hand, a few geometric rules turn landmarks into gestures, and pyautogui drives the mouse.


## Gestures

There are two control schemes. Pick one in `config.py` (`SCHEME = "pinch"`
or `"fist"`) or for a single run:

```bash
uv run handsoff --scheme fist
```

The pose name in the tables is what the preview window prints while the pose
is active, so you can check what the rules are seeing. Pointing and scrolling
work the same in both schemes; only the clicking differs.

### Scheme `pinch` (default)

| Pose           | How to do it                                                | What happens                                   |
| -------------- | ----------------------------------------------------------- | ---------------------------------------------- |
| `point`        | Raise only your index finger, curl the other three.         | The cursor follows your index fingertip.       |
| `pinch`        | Touch thumb tip to index fingertip.                         | Left button is held. Tap = click. Hold and move = drag. |
| `middle_pinch` | Touch thumb tip to **middle** fingertip.                    | One right click, fired the moment the pinch starts. |
| `scroll`       | Raise index and middle fingers ("peace" sign), then move the hand up or down. | Page scrolls with your hand. Cursor stays put. |
| anything else  | Open palm, fist, hand out of view.                          | Nothing. Use this to rest.                     |

### Scheme `fist`

| Pose           | How to do it                                                | What happens                                   |
| -------------- | ----------------------------------------------------------- | ---------------------------------------------- |
| `point`        | Raise only your index finger.                               | The cursor follows your index **knuckle** (see note below). |
| `fist`         | Close your hand.                                            | Left button is held. Tap = click. Hold and move = drag. |
| `fist` twice   | Fist, open, fist again within 1 second.                     | Right click on the second fist.                |
| `scroll`       | Peace sign, move the hand up or down.                       | Page scrolls with your hand.                   |
| `hand_down`    | Point your fingers at the floor.                            | Presses Page Up once. Raise the hand and dip again for another. |
| `middle`       | Raise only your middle finger and hold it for 2 seconds.    | The app quits.                                 |
| anything else  | Open palm, pinches, hand out of view.                       | Nothing. Use this to rest.                     |

The cursor follows the knuckle rather than the fingertip in this scheme
because closing your hand to click moves the fingertip a whole palm-length
downward, which would throw the click off target. The knuckle barely moves.

Two fists also send two left clicks on the way to the right click, the same
way a mouse double-click does. This is a deliberate trade-off: suppressing
them would mean delaying every single click by the double-fist window.

### Tips for reliable recognition

- Keep your hand roughly upright, fingers toward the ceiling, palm facing the
  camera. The "finger up" rule compares fingertip height to the knuckle, so a
  sideways hand confuses it.
- Only the central part of the camera view is mapped to the screen, so small
  hand movements are enough to cross the whole display.
- To click without the cursor drifting, stop moving first, then pinch or fist.
- Return to an open palm between two different click poses, otherwise the
  rules can briefly read the transition as something else.

All thresholds and timings are in [src/handsoff/config.py](src/handsoff/config.py).
The pose rules are in [src/handsoff/gestures.py](src/handsoff/gestures.py) and
the pose-to-action mapping for each scheme is in
[src/handsoff/actions.py](src/handsoff/actions.py).

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

Add `--scheme fist` to use the fist-based controls. A preview window shows
the webcam feed with landmarks, the current pose name and the active scheme.
Press `q` in that window, Ctrl+C in the terminal, or (fist scheme only) hold
up your middle finger for 2 seconds to quit.

## Test

```bash
uv run pytest
```

The tests cover only the pure logic (gesture rules, coordinate mapping,
smoothing) and need no webcam.

## Tuning

Every threshold lives in [src/handsoff/config.py](src/handsoff/config.py):

- Cursor shaky? Lower `SMOOTHING_ALPHA`. Cursor laggy? Raise it.
- Pinch clicks not registering? Raise `PINCH_RATIO`. Ghost clicks? Lower it.
- Fist not detected? Raise `FIST_RATIO`. Pinches being read as fists? Lower it.
- Double fist too hard to hit? Raise `DOUBLE_FIST_WINDOW`.
- Can't reach the screen edge? Raise `FRAME_MARGIN`.
- Wrong camera? Change `CAMERA_INDEX`.

## Learning path

See [master.md](master.md) for a guided, file-by-file tour of the code.
