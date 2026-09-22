# terminal.md: every command run while building this project, and why

Commands are listed in the order they were run. Paths are relative to the
project root. Commands whose only purpose was inspection (listing files,
printing a file) are included too, because they explain the decisions that
followed them.

---

## 1. Inspect the environment

```bash
ls -la
uv --version
uv python list
```

**Why:** confirm the folder was empty, that `uv` was installed (0.11.15), and
which Python versions were available. Python 3.11 was already on the machine,
and MediaPipe publishes wheels for it, so 3.11 was chosen as the minimum.

---

## 2. Scaffold the project

```bash
uv init --package --name handsoff --python 3.11 .
```

**Why:** `uv init` creates `pyproject.toml`, `.python-version`, `.gitignore`,
a `README.md` stub and a git repo. The `--package` flag chooses the
`src/handsoff/` layout with a build backend and a `[project.scripts]` entry,
which is what lets `uv run handsoff` work later. Without `--package` you get
a flat single-script layout, which the project brief asked to avoid.

---

## 3. Add dependencies

```bash
uv add mediapipe opencv-python pyautogui
uv add --dev pytest
```

**Why:** `uv add` writes the dependency into `pyproject.toml`, resolves the
full dependency tree, pins every version in `uv.lock`, and installs into
`.venv/` in one step. This replaces `pip install` plus a hand-maintained
`requirements.txt`. `--dev` puts pytest in the `dev` dependency group so it
is not installed for people who only want to run the app.

---

## 4. Check what the installed MediaPipe supports

```bash
cat pyproject.toml
find . -path ./.venv -prune -o -type f -print
uv run python -c "import mediapipe as mp; print(mp.__version__); print(hasattr(mp,'solutions'))"
```

**Why:** most online tutorials use `mp.solutions.hands`, the old "Solutions"
API. The check showed `uv` had installed MediaPipe 1.0.1, which has removed
that API entirely (`hasattr` printed `False`). That decided the design of
`tracker.py`: it uses the newer Tasks API (`HandLandmarker`), which needs a
model file on disk.

`uv run python -c ...` runs Python inside the project's `.venv` without
activating it manually.

---

## 5. Verify the Tasks API and fetch the model

```bash
uv run python -c "from mediapipe.tasks.python import vision; import inspect; print(inspect.signature(vision.HandLandmarkerOptions))"
curl -sSL -o src/handsoff/hand_landmarker.task https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
```

**Why:** the first command printed the constructor signature of
`HandLandmarkerOptions` so the tracker could be written against the real
parameter names (`num_hands`, `running_mode`, etc.) instead of guessed ones.
The `curl` downloaded Google's pre-trained hand landmark model (~8 MB) so
the app could be smoke-tested locally.

---

## 6. Move the model out of the package and ignore it in git

```bash
mkdir -p models tests
mv src/handsoff/hand_landmarker.task models/
printf '\n# Downloaded MediaPipe model (fetched automatically on first run)\nmodels/\n' >> .gitignore
```

**Why:** an 8 MB binary should not live in the Python package or in git
history. It was moved to a top-level `models/` folder, that folder was added
to `.gitignore`, and `tracker.py` was written to download it automatically
on first run if it is missing. `tests/` was created at the same time for the
unit tests.

---

## 7. Write the source files

The first attempt used one long `bash` heredoc to write all six modules at
once. It failed to parse (a quoting issue in the multi-file script), so each
file was written individually with the editor's file-write tool instead.
Files written, in order:

- `src/handsoff/config.py`
- `src/handsoff/tracker.py`
- `src/handsoff/gestures.py`
- `src/handsoff/smoothing.py`
- `src/handsoff/mapping.py`
- `src/handsoff/controller.py`
- `src/handsoff/main.py`
- `src/handsoff/__init__.py` (replaced uv's placeholder `main()` with a docstring)
- `tests/test_gestures.py`
- `tests/test_mapping_smoothing.py`

---

## 8. Fix up `pyproject.toml`

```bash
sed -i 's|handsoff = "handsoff:main"|handsoff = "handsoff.main:main"|; s|description = "Add your description here"|description = "Control the desktop cursor ..."|' pyproject.toml
printf '\n[tool.pytest.ini_options]\ntestpaths = ["tests"]\n' >> pyproject.toml
```

**Why:** `uv init` pointed the `handsoff` command at a placeholder `main()`
in `__init__.py`. The `sed` re-points it at `main()` in `main.py` and fills
in the description. The appended pytest section tells pytest where the tests
live so plain `uv run pytest` works from the project root.

---

## 9. Run the tests

```bash
uv run pytest -q
```

**Why:** verify the pure logic (gesture rules, mapping, smoothing). `uv run`
noticed `pyproject.toml` had changed and rebuilt/reinstalled the package
into `.venv` before running. Result: 15 passed.

---

## 10. Smoke-test the hardware-facing code without a webcam

```bash
uv run python -c "
import numpy as np
from handsoff.tracker import HandTracker
t = HandTracker()
frame = np.zeros((480, 640, 3), dtype=np.uint8)
print(t.detect(frame))
t.close()
from handsoff.controller import DesktopController
print(DesktopController().screen_w)
from handsoff.main import main
"
```

**Why:** the tests deliberately avoid MediaPipe and pyautogui, so this
one-off script checks the parts they skip: the model loads, `detect()` runs
on a blank frame and returns `None` (no hand) without crashing, pyautogui can
read the screen size, and `main.py` imports cleanly. It does not move the
mouse.

---

## 11. Check that a webcam opens

```bash
uv run python -c "import cv2; c = cv2.VideoCapture(0); print(c.isOpened()); c.release()"
```

**Why:** confirm `CAMERA_INDEX = 0` is a real camera on this machine before
declaring the project runnable. The full app was not launched from the
build session because it takes over the mouse.

---

## 12. Add the second control scheme (later session)

No new dependencies were needed. Files changed or added:

- `src/handsoff/gestures.py`: added FIST, MIDDLE_FINGER and HAND_DOWN poses,
  renamed RIGHT_PINCH to MIDDLE_PINCH (it is a shape, not an action).
- `src/handsoff/actions.py` (new): pose -> action mapping for each scheme,
  plus the double-fist and hold-to-quit timers.
- `src/handsoff/config.py`: `SCHEME`, `FIST_RATIO`, `DOUBLE_FIST_WINDOW`,
  `QUIT_HOLD_SECONDS`.
- `src/handsoff/controller.py`: `page_up()`.
- `src/handsoff/main.py`: `--scheme` flag; loop now drives the controller
  from an `Actions` object.
- `tests/test_actions.py` (new), `tests/test_gestures.py` (updated).

```bash
uv run pytest -q
```

**Why:** the pose rules gained three new cases and a new ordering, and the
mapper has time-based logic. Both are covered by tests that fake the clock,
so this one command verifies everything without a webcam. Result: 31 passed.

```bash
uv run handsoff --help
uv run python -c "from handsoff.main import main; from handsoff.actions import ActionMapper; print(ActionMapper('fist').cursor_landmark)"
```

**Why:** confirm the `--scheme {pinch,fist}` flag is registered by argparse
and that the new module imports cleanly alongside the old ones. As before,
the app itself was not launched from the build session because it takes
over the mouse.

---

## Commands you will use day to day

```bash
uv sync           # create/refresh .venv from uv.lock
uv run handsoff                # run the app (pinch scheme)
uv run handsoff --scheme fist  # run with the fist scheme
uv run pytest     # run the tests
uv add <pkg>      # add a dependency (updates pyproject.toml and uv.lock)
```
