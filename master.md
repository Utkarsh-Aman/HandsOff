# master.md: a learning path through HandsOff

This is a guided reading order for the codebase. Each step names one file,
what to look for, and the general concept it teaches. Read the files in this
order; each builds on the previous one. The whole tour is about 600 lines of
Python, roughly half of it docstrings and tests, and fits in one sitting.

The pipeline you are about to read, in one line:

```
webcam frame -> HandTracker -> 21 landmarks -> classify() -> Gesture
                                    |                            |
                            ExponentialSmoother          DesktopController
                                    |                            |
                              map_to_screen  ---------->  pyautogui (OS)
```

---

## Step 0: Run it first

```bash
uv sync
uv run handsoff
```

Wave your hand, point, pinch. Watch the preview window: the green dots are the
landmarks, the yellow text is the gesture the rules decided on. Now you know
what the code has to produce, so the code will make sense.

Also run `uv run pytest` and note that the tests finish in a fraction of a
second with no webcam. Remember that; it is the payoff of step 3.

---

## Step 1: `pyproject.toml` and `uv.lock`

**Concept: declaring a project and locking its dependencies.**

Look for:
- `[project] dependencies`: the three libraries the app actually needs.
- `[dependency-groups] dev`: pytest, needed only for development.
- `[project.scripts]`: this line is why `uv run handsoff` works. It maps a
  command name to `handsoff.main:main` (module path, colon, function).
- `uv.lock`: exact versions of every transitive dependency. You never edit
  it; `uv add` and `uv sync` maintain it so everyone gets identical installs.
- The `src/handsoff/` layout: the package lives under `src/` so that tests
  import the *installed* package, not whatever happens to be in the current
  directory.

---

## Step 2: `src/handsoff/config.py`

**Concept: config separation. Put every tunable number in one place.**

Look for:
- Each constant has a comment saying what happens if you change it. That is
  the point: when the cursor feels wrong you come here, not to the algorithm.
- `MODEL_PATH` is computed relative to this file with `pathlib`, so the app
  works no matter which directory you run it from.
- Notice what is *not* here: no config file parsing, no CLI flags, no
  environment variables. Python constants are the simplest thing that works.

---

## Step 3: `src/handsoff/gestures.py`

**Concept: rule-based classification with pure functions.**

This is the heart of the project. Look for:
- The landmark index constants at the top. MediaPipe returns 21 points in a
  fixed order; naming the indices (`INDEX_TIP = 8`) is what makes the rules
  readable.
- `finger_is_up()`: one comparison. A finger is up if its tip's y is smaller
  than its middle joint's y. Note *why smaller*: image coordinates grow
  downward. Note also the stated assumption (hand is upright) and its
  limitation.
- `is_pinching()`: read the docstring about dividing by palm length. This is
  the single most important trick in the file. A raw distance threshold would
  break as soon as you moved closer to or further from the camera.
- `classify()`: rules are checked in a deliberate order and the docstring
  explains why pinches go first. Ordering is a design decision, not an
  accident.
- Nothing in this file imports OpenCV, MediaPipe, or pyautogui. Landmarks in,
  `Gesture` out. That is what "pure" means here and it is what makes step 8
  possible.

---

## Step 4: `src/handsoff/smoothing.py`

**Concept: signal smoothing with an exponential moving average.**

Look for:
- The one-line formula in the class docstring. Everything else is
  bookkeeping around it.
- The `alpha` trade-off: responsiveness versus smoothness. There is no
  correct value, only a feel you tune in `config.py`.
- The two edge cases and why they exist: the first sample passes through
  unchanged (no "fly in" from the corner), and `reset()` forgets history when
  the hand disappears (no glide when it comes back).
- This class holds state (`_prev`) but still has no side effects. It is a
  small state machine, and still fully testable.

---

## Step 5: `src/handsoff/mapping.py`

**Concept: coordinate transforms and clamping.**

Look for:
- The three-step transform: shift by the margin, stretch by the usable
  fraction, clamp to [0, 1], scale to pixels. Work one example by hand:
  with margin 0.15, where does nx = 0.5 land? Where does nx = 0.1 land?
- Why `screen_w - 1`: pixel coordinates are 0-indexed.
- Why this is its own tiny module: it is math, not OS control, so it does
  not belong next to pyautogui, and it is not a gesture rule either.

---

## Step 6: `src/handsoff/tracker.py`

**Concept: wrapping a third-party model behind a small interface.**

Look for:
- The public surface is tiny: `HandTracker.detect(frame) -> list | None`.
  Everything MediaPipe-specific (options objects, running modes, `mp.Image`,
  timestamps) is hidden inside. If MediaPipe changes its API again, only
  this file changes.
- `detect()` converts *out* of MediaPipe's types into plain tuples before
  returning. The rest of the program never sees a MediaPipe object.
- The BGR-to-RGB flip via `[..., ::-1]`. OpenCV and MediaPipe disagree on
  channel order; this is a classic source of silent bugs.
- `ensure_model_downloaded()`: the model file is fetched on first run rather
  than committed to git. Note the trade-off (needs internet once) and why it
  was chosen (keeps the repo small).

---

## Step 7: `src/handsoff/controller.py`

**Concept: isolating side effects. Decide elsewhere, act here.**

Look for:
- This is the only file that imports pyautogui. Everything else can be run
  and tested with no mouse moving.
- The two module-level settings, `PAUSE = 0` and `FAILSAFE = False`, each
  with a comment explaining what would go wrong without them.
- `set_left_button(down)`: called every frame with a boolean, but only sends
  a press or release when the boolean *changes*. That one idea gives you
  click and drag with no timers or cooldowns. Compare it with `right_click()`,
  which is a one-shot action; the caller has to decide when to fire it.
- `release_all()`: cleanup that prevents a stuck mouse button on exit.

---

## Step 8: `src/handsoff/main.py`

**Concept: a thin composition layer, and level- vs edge-triggered actions.**

Look for:
- `main()` only builds objects, calls `run()`, and cleans up in `finally`.
  The `finally` matters: the cleanup runs on Ctrl+C, on an exception, and on
  a normal `q` alike.
- `run()` is the whole pipeline in about 40 lines. Read it top to bottom:
  capture, mirror, detect, classify, smooth, act, draw.
- `cv2.flip(frame, 1)`: the mirror. Comment out that line and run the app to
  feel why it is there.
- The two bits of carried-over state, `prev_gesture` and `prev_y`, and what
  each one enables (transitions and scroll deltas).
- The distinction in the comments between *level-triggered* (left button:
  held while the pinch is held) and *edge-triggered* (right click: fires
  once on the frame the pinch begins). This pattern shows up everywhere in
  event-driven code.
- The smoother is updated on every frame the hand is visible, not only when
  moving the cursor. The comment explains the bug that avoids.

---

## Step 9: `tests/test_gestures.py` and `tests/test_mapping_smoothing.py`

**Concept: testing pure functions with hand-built inputs.**

Look for:
- `make_hand()`: a helper that constructs 21 landmarks from a few keyword
  arguments. Most of the test file's value is in making test cases *read*
  like the gesture they describe: `make_hand(index=True, middle=True)`.
- `test_pinch_wins_over_finger_pattern`: a test that pins down the rule
  ordering from step 3. If someone reorders `classify()`, this fails.
- `test_pinch_is_scale_invariant`: shrinks the whole hand and asserts the
  verdict is unchanged. This is the test that justifies dividing by palm
  length.
- The mapping tests work one concrete example each, including the clamp.
- None of these tests mock anything. That is only possible because steps 3
  to 5 kept the logic pure. If `classify()` called pyautogui, every test
  would need a fake mouse.

---

## What you should now be able to explain

- Why thresholds live in `config.py` and not next to the code that uses them.
- How 21 (x, y) points become a gesture with no machine learning.
- Why the pinch rule divides by palm length.
- What the EMA formula does, and what changing alpha feels like.
- Why only `controller.py` imports pyautogui.
- The difference between level-triggered and edge-triggered actions.
- Why the tests need no webcam.

---

## Suggested extensions (once the base project makes sense)

Roughly in order of difficulty:

1. **Tune the smoothing.** Try `SMOOTHING_ALPHA` values from 0.1 to 0.9 and
   feel the lag/jitter trade-off. Then try a smarter version: use a high
   alpha when the hand moves fast and a low one when it is nearly still
   (this is the idea behind the "One Euro filter").
2. **Stop the cursor drifting during a pinch.** When you bring thumb and
   index together, the index tip moves, so the click lands slightly off
   target. Ideas: drive the cursor from the index MCP joint instead of the
   tip, or freeze the cursor for a few frames when a pinch begins.
3. **Add a horizontal scroll** using left/right motion in the SCROLL pose
   (`pyautogui.hscroll`).
4. **Add a "pause" gesture.** An open palm could toggle the controller on
   and off so you can use the real mouse without quitting.
5. **Debounce gestures.** Require a gesture to be seen for N consecutive
   frames before acting on it. This removes one-frame misclassifications
   (ghost right-clicks) at the cost of a few frames of latency.
6. **Double click.** Detect two pinches within a short time window. You will
   need a timestamp, which is your first piece of time-based state.
7. **Support a second hand.** Set `num_hands=2` in the tracker, return both
   hands (with handedness), and give each a role: one moves, the other
   clicks. Think about what changes in `classify()` and `run()`.
8. **Relative (trackpad-style) movement.** Instead of mapping the frame
   absolutely to the screen, move the cursor by the *delta* of the fingertip
   each frame. This removes the reach problem entirely but changes the feel.
9. **Log landmarks to a CSV** while you perform each gesture, then plot the
   pinch ratio over time. Use the plot to pick `PINCH_RATIO` from data
   instead of guessing. This is the honest, non-ML way to tune a threshold.
