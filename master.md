# master.md: a learning path through HandsOff

This is a guided reading order for the codebase. Each step names one file,
what to look for, and the general concept it teaches. Read the files in this
order; each builds on the previous one. The whole tour is under 1000 lines of
Python, roughly half of it docstrings and tests, and fits in one sitting.

The pipeline you are about to read, in one line:

```
webcam frame -> HandTracker -> 21 landmarks -> classify() -> Gesture (pose)
                                    |                            |
                            ExponentialSmoother            ActionMapper (scheme)
                                    |                            |
                              map_to_screen  ---->  DesktopController -> pyautogui (OS)
```

---

## Step 0: Run it first

```bash
uv sync
uv run handsoff
uv run handsoff --scheme fist
```

Wave your hand, point, pinch, make a fist. Watch the preview window: the
green dots are the landmarks, the yellow text is the pose the rules decided
on, the grey text is the active scheme. Now you know what the code has to
produce, so the code will make sense.

Also run `uv run pytest` and note that the tests finish in a fraction of a
second with no webcam. Remember that; it is the payoff of steps 3 and 4.

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
- `SCHEME` is the one setting that changes *behaviour* rather than a
  threshold. It is still just a string constant; the code that interprets
  it lives elsewhere (step 4).
- The timing constants (`DOUBLE_FIST_WINDOW`, `QUIT_HOLD_SECONDS`) are in
  seconds, not frames. Frame rate varies between machines; seconds don't.
- `MODEL_PATH` is computed relative to this file with `pathlib`, so the app
  works no matter which directory you run it from.
- Notice what is *not* here: no config file parsing, no environment
  variables. Python constants are the simplest thing that works.

---

## Step 3: `src/handsoff/gestures.py`

**Concept: rule-based classification with pure functions.**

This is the heart of the project. Look for:
- The landmark index constants at the top. MediaPipe returns 21 points in a
  fixed order; naming the indices (`INDEX_TIP = 8`) is what makes the rules
  readable.
- The `Gesture` enum describes hand *shapes* only. Nothing here says "click".
  That separation is what lets two schemes share one classifier.
- `palm_length()`: the hand's size unit. Every distance rule divides by it
  so the rule works at any distance from the camera. This is the single most
  important trick in the file.
- `finger_is_up()`: one comparison. A finger is up if its tip's y is smaller
  than its middle joint's y. Note *why smaller*: image coordinates grow
  downward. Note also the stated assumption (hand is upright).
- `is_fist()` measures tip-to-wrist distance instead of reusing
  `finger_is_up()`. The docstring explains why: a pinching finger also fails
  the "up" test, so "all fingers down" would confuse a pinch with a fist.
- `classify()`: rules are checked in a deliberate order and the docstring
  gives a reason for each placement. Ordering is a design decision, not an
  accident, and step 10's tests pin it down.
- Nothing in this file imports OpenCV, MediaPipe, or pyautogui. Landmarks in,
  `Gesture` out. That is what "pure" means here.

---

## Step 4: `src/handsoff/actions.py`

**Concept: separating "what is the hand doing" from "what should happen",
and handling time without side effects.**

Look for:
- `Actions` is a dataclass of booleans. Several can be true at once (a drag
  is `move` + `hold_left`), which is why it is not an enum.
- `CURSOR_LANDMARK`: the fist scheme tracks the knuckle, not the fingertip.
  Read the comment; it is a concrete example of a gesture's *side effect on
  tracking* forcing a design decision.
- `update(gesture, now)`: the clock is passed in, never read inside. That is
  the whole reason `tests/test_actions.py` can test a 2-second hold in
  microseconds.
- `started = gesture != self._prev`: one line that turns a per-frame stream
  into transitions. Every edge-triggered action (right click, page up) hangs
  off it.
- The double-fist logic: a timestamp, a window, and a "consume" step so a
  third fist starts fresh. The docstring is honest about the trade-off (two
  left clicks also happen).
- The two scheme methods are plain `if` logic on the enum. No plugin
  registry, no dictionary of callables. Two schemes do not earn that.

---

## Step 5: `src/handsoff/smoothing.py`

**Concept: signal smoothing with an exponential moving average.**

Look for:
- The one-line formula in the class docstring. Everything else is
  bookkeeping around it.
- The `alpha` trade-off: responsiveness versus smoothness. There is no
  correct value, only a feel you tune in `config.py`.
- The two edge cases and why they exist: the first sample passes through
  unchanged (no "fly in" from the corner), and `reset()` forgets history when
  the hand disappears (no glide when it comes back).
- This class holds state (`_prev`) but still has no side effects. Like the
  mapper in step 4, it is a small state machine that is fully testable.

---

## Step 6: `src/handsoff/mapping.py`

**Concept: coordinate transforms and clamping.**

Look for:
- The three-step transform: shift by the margin, stretch by the usable
  fraction, clamp to [0, 1], scale to pixels. Work one example by hand:
  with margin 0.15, where does nx = 0.5 land? Where does nx = 0.1 land?
- Why `screen_w - 1`: pixel coordinates are 0-indexed.
- Why this is its own tiny module: it is math, not OS control, so it does
  not belong next to pyautogui, and it is not a gesture rule either.

---

## Step 7: `src/handsoff/tracker.py`

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

## Step 8: `src/handsoff/controller.py`

**Concept: isolating side effects. Decide elsewhere, act here.**

Look for:
- This is the only file that imports pyautogui. Everything else can be run
  and tested with no mouse moving.
- The two module-level settings, `PAUSE = 0` and `FAILSAFE = False`, each
  with a comment explaining what would go wrong without them.
- `set_left_button(down)`: called every frame with a boolean, but only sends
  a press or release when the boolean *changes*. That one idea gives you
  click and drag with no timers. Compare it with `right_click()` and
  `page_up()`, which are one-shot; the mapper decides when to fire them.
- `release_all()`: cleanup that prevents a stuck mouse button on exit.

---

## Step 9: `src/handsoff/main.py`

**Concept: a thin composition layer.**

Look for:
- `parse_args()`: one `argparse` flag whose default comes from `config.py`.
  That is the whole "select between two schemes" feature at the CLI level.
- `main()` only builds objects, calls `run()`, and cleans up in `finally`.
  The `finally` matters: the cleanup runs on Ctrl+C, on an exception, on a
  normal `q`, and on the quit gesture alike.
- `run()` is the whole pipeline. Read it top to bottom: capture, mirror,
  detect, classify, map to actions, smooth, act, draw.
- `cv2.flip(frame, 1)`: the mirror. Comment out that line and run the app to
  feel why it is there.
- How little state the loop holds now: just `prev_y` for scrolling. The
  transition and timer logic moved into the mapper in step 4, and the loop
  got simpler as a result. Compare the `if actions.x:` block with the
  controller's methods; it is almost a one-to-one translation.
- The smoother is updated on every frame the hand is visible, not only when
  moving the cursor. The comment explains the bug that avoids.

---

## Step 10: `tests/`

**Concept: testing pure functions and injected time.**

Three files:
- `test_gestures.py`: `make_hand()` builds 21 landmarks from a few keyword
  arguments so test cases *read* like the pose: `make_hand(index=True,
  middle=True)`. Look at `test_fist_wins_over_pinch` and
  `test_pinch_wins_over_finger_pattern`: they pin down the rule ordering
  from step 3. `test_pinch_is_scale_invariant` justifies dividing by palm
  length.
- `test_actions.py`: feeds poses with fake timestamps. `test_middle_finger_
  quits_only_after_hold` tests a 2-second behaviour without waiting 2
  seconds. That is only possible because `update()` takes `now` as an
  argument. `frames()` is a five-line helper that simulates 30 fps.
- `test_mapping_smoothing.py`: one concrete example per transform,
  including the clamp.

None of these tests mock anything. If `classify()` called pyautogui, or the
mapper read the system clock, every test would need a fake mouse or a sleep.

---

## What you should now be able to explain

- Why thresholds live in `config.py` and not next to the code that uses them.
- How 21 (x, y) points become a pose with no machine learning.
- Why the distance rules divide by palm length.
- Why poses and actions are separate types, and what that buys you.
- Why the mapper takes `now` as a parameter.
- What the EMA formula does, and what changing alpha feels like.
- Why only `controller.py` imports pyautogui.
- The difference between level-triggered and edge-triggered actions.
- Why the tests need no webcam and no sleeping.

---

## Suggested extensions (once the base project makes sense)

Roughly in order of difficulty:

1. **Tune the smoothing.** Try `SMOOTHING_ALPHA` values from 0.1 to 0.9 and
   feel the lag/jitter trade-off. Then try a smarter version: use a high
   alpha when the hand moves fast and a low one when it is nearly still
   (this is the idea behind the "One Euro filter").
2. **Add Page Down.** The fist scheme has Page Up on `hand_down`. Design a
   pose for Page Down and wire it through `Gesture`, `Actions`, the mapper
   and the controller. You will touch four files; notice that each change
   is one or two lines.
3. **Add a horizontal scroll** using left/right motion in the SCROLL pose
   (`pyautogui.hscroll`).
4. **Suppress the left clicks in a double fist.** Delay the left press by
   `DOUBLE_FIST_WINDOW` and cancel it if a second fist arrives. Feel the
   latency cost, then decide whether it was worth it.
5. **Debounce poses.** Require a pose to be seen for N consecutive frames
   before the mapper acts on it. This removes one-frame misclassifications
   (ghost right-clicks) at the cost of a few frames of latency.
6. **Add a "pause" gesture.** An open palm held for a second could toggle
   the controller on and off so you can use the real mouse without quitting.
   The hold-to-quit code is your template.
7. **Support a second hand.** Set `num_hands=2` in the tracker, return both
   hands (with handedness), and give each a role: one moves, the other
   clicks. Think about what changes in `classify()` and the mapper.
8. **Relative (trackpad-style) movement.** Instead of mapping the frame
   absolutely to the screen, move the cursor by the *delta* of the tracked
   landmark each frame. This removes the reach problem entirely.
9. **Log landmarks to a CSV** while you perform each pose, then plot the
   pinch and fist ratios over time. Use the plot to pick `PINCH_RATIO` and
   `FIST_RATIO` from data instead of guessing. This is the honest, non-ML
   way to tune a threshold.
