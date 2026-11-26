# User tests

> **Status:** Current · **Updated:** 2026-11-25

Checks that need the owner: watching it run and judging it, at the desktop now, and on
the real devices (Pis, projectors, radar, lights) from Stage 1. Automated tests and
offscreen renders can't show these: how it looks on a real screen, the real frame rate,
how a visit *feels*. They are the owner's part of the
[verification plan](requirements/verification-plan.md) (mostly its *demonstration*
events, VE-…).

Two kinds:
- **Desktop tests:** the simulator in real windows at the desktop (Stage 0).
- **Device tests:** the real hardware (Stage 1 on). Each Stage's CDR plans its own.

## Rules (from cairn's device passes, adapted)

1. **File before the merge.** When a build step leaves a check that only the owner can
   do, it is written here, with its own ID, before the step merges. A check that is owed
   but not written down gets lost.
2. **It doesn't hold up the merge.** A step merges when its code and automated tests are
   done (owner, 2026-11-25). The user test runs afterwards. Whatever it turns up becomes
   the next step's first work, not a reopening of the merged step.
3. **Record evidence.** Each run notes the date, a verdict (**pass**, **fail** or
   **ambiguous**), what was seen, and what to change. A one-word "fine" isn't evidence.
4. **Close it on its own.** Ticking a build step in the plan doesn't close its user
   test. The step's plan entry links here and stays open until the test passes.

## Owed

| ID | Kind | What | From | Owed since | VE | Verdict |
|---|---|---|---|---|---|---|
| [UT-001](#ut-001) | desktop | Both eyes in real windows, 60 fps | Step 2 | 2026-11-23 | VE-002 | owed |
| [UT-002](#ut-002) | desktop | The eyes follow a kid on the fake radar | Step 3 | 2026-11-23 | VE-005 | owed |
| [UT-003](#ut-003) | desktop | A pretend visit feels right | Step 4 | 2026-11-25 | VE-005 | owed |

All three can be done in one sitting at the desktop, with the broker running and each
command in its own terminal. UT-003's setup covers UT-002.

### UT-001

**Both eyes in real windows, 60 fps.** Deferred by the owner on 2026-11-23
([Step 2](stage-0-plan.md#step-2--eye-renderer-first-version-november)).

- **Run:** both eye windows on the desktop screen, driven over MQTT (`eyes/README.md`).
- **Pass when:** each window is shaped like its real window, the eyes blink, change
  expression and glide to look-at points, at a steady 60 fps measured on the monitor
  (vsync). The offscreen GPU renders can't measure this.
- **Result:** _not yet run._

### UT-002

**The eyes follow a kid on the fake radar**
([Step 3 results](results/stage-0-step-3/README.md)).

- **Run:** as UT-003.
- **Pass when:** dragging a kid makes both eyes follow, each at its own angle.
- **Result:** _not yet run._

### UT-003

**A pretend visit feels right**: Step 4's "done when"
([Step 4 results](results/stage-0-step-4/README.md)).

- **Run:**

  ```bash
  .venv/bin/python -m eyes --side left
  .venv/bin/python -m eyes --side right
  .venv/bin/python -m sim.fake_fpp
  .venv/bin/python -m brain --any-time
  .venv/bin/python -m sim.fake_radar
  ```

  Drag a kid from the sidewalk up the path, to the door, and away; then try two kids.
- **Judge** (tune in `themes/halloween/settings.yaml`, or tell Claude):
  - the faces: Watching `happy`, and a 0.8 s `surprised` glance at a new kid coming;
  - the timings: goodbye 5 s, sleep 20 s, comments 10–20 s with a 10 s gap, focus
    holds 3–6 s, blinks 2.5–6 s, door hold 15 s (TBD-028);
  - asleep: a droopy flutter with each snore, every 30 s;
  - whether a short visit is too quiet (the 10 s gap can push comments out).
- **Pass when:** a visit plays through from asleep to goodbye and back to sleep, and it
  feels right to the owner.
- **Result:** _not yet run._

## Done

_None yet._ Move a test here with its verdict and date when it passes.
