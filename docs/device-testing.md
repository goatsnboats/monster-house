# Device testing

> **Status:** Current · **Updated:** 2026-11-25

Checks that need the owner at a real screen or device: things the automated tests and
offscreen renders can't show, like how it looks on the monitor, real frame rate, and how
a visit *feels*. Each item says where it came from and how to run it. Tick it here (with
the date) once done, and note anything to change.

## Stage 0, at the desktop

All of these can run in one sitting at the desktop with the broker running. Each
command goes in its own terminal.

- [ ] **Both eyes in real windows, 60 fps** (Step 2, deferred by the owner 2026-11-23).
  Both eye windows on the desktop screen, driven over MQTT, with the frame rate measured
  on the monitor (vsync). See [Step 2](stage-0-plan.md#step-2--eye-renderer-first-version-november)
  and `eyes/README.md`.
- [ ] **The eyes follow a kid on the fake radar** (Step 3,
  [results](results/stage-0-step-3/README.md)). All programs together in real windows.
  Now covered by the Step 4 visit below.
- [ ] **A pretend visit feels right** (Step 4's "done when",
  [results](results/stage-0-step-4/README.md), added 2026-11-25). Run:

  ```bash
  .venv/bin/python -m eyes --side left
  .venv/bin/python -m eyes --side right
  .venv/bin/python -m sim.fake_fpp
  .venv/bin/python -m brain --any-time
  .venv/bin/python -m sim.fake_radar
  ```

  Then drag a kid from the sidewalk up the path, to the door, and away; then try two
  kids. Judge, and tune in `themes/halloween/settings.yaml` or tell Claude:
  - the faces: Watching `happy`, and a 0.8 s `surprised` glance at a new kid coming;
  - the timings: goodbye 5 s, sleep 20 s, comments 10–20 s with a 10 s gap, focus
    holds 3–6 s, blinks 2.5–6 s, door hold 15 s (TBD-028);
  - asleep: a droopy flutter with each snore, every 30 s;
  - whether a visit is too quiet (the 10 s gap can push comments out of a short visit).
