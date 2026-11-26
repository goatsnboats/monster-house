# brain/ — the monster brain

The one place where decisions are made: moods (Asleep → Waking → Greeting → Watching →
Goodbye), who to look at, blinks and voice clips. See `docs/architecture.md` §3b.
The phone page comes in Step 6.

**Status:** Stage 0 Step 4, first version (2026-11-25). Results:
[docs/results/stage-0-step-4/](../docs/results/stage-0-step-4/README.md).

## How to run it

With the broker running, from the repository root:

```bash
.venv/bin/python -m brain --any-time
```

Outside the theme's show hours (`themes/halloween/settings.yaml`, TBD-024) the monster
stays asleep; `--any-time` ignores them, for daytime trials. `--theme` picks another
theme folder.

**A pretend visit in real windows:** run these in five terminals, then drag a kid up the
path in the fake radar.

```bash
.venv/bin/python -m eyes --side left
.venv/bin/python -m eyes --side right
.venv/bin/python -m sim.fake_fpp          # add --sound once there are .wav files
.venv/bin/python -m brain --any-time
.venv/bin/python -m sim.fake_radar
```

Watch the mood with `.venv/bin/python -m shared.mqtt_tool sub state`, and the clips in
the fake FPP's terminal. **Without windows:** `.venv/bin/python -m sim.pretend_visit`
plays a scripted visit and prints what the brain did, second by second.

## What it does

| | |
|---|---|
| Wakes | when a kid is **coming** toward the house inside the approach range (5 m) |
| Looks | at one kid, 10 times a second: a new arrival wins, then 3–6 s each, preferring kids coming, closest breaks ties; a kid going away is watched until they leave; a kid lost at the door is looked for at the door point for the door hold (15 s) |
| Blinks | both eyes, every 2.5–6 s while awake, and on each switch between kids |
| Talks | wake, then greet, then a comment every 10–20 s; bye for a kid going and on goodbye; at least 10 s between lines (the greeting follows the yawn straight away) |
| Fails friendly | radar offline: eyes open and wander, no visits, no voice. An eye offline: logged, carry on; when it's back it is told the current face. FPP silent for 2 s: carries on without voice |

All timings and clip pools come from the theme (ICD-005); the radar, door and eye
positions from `config/site.yaml` (ICD-015). The few numbers in code are how the face
moves (expression ease 0.4 s, look-around 1.5 s, droop after 2 s, glance 0.8 s) and how
visitors are tracked (smoothing 0.15 s, coming/going over 0.5 s).

## Code

- `core.py`: puts it all together; `on_message` in, `tick` out (no MQTT, so tests drive it).
- `moods.py`: the mood state machine, on a clock.
- `visitors.py`: radar slots → visitors: smoothing, coming/going, door hold.
- `focus.py`: which visitor to look at.
- `gaze.py`: the look point for a visitor (head height, or the door point).
- `clips.py`: clip pools (shuffle, no repeats), minimum gap, clip finished (ICD-003).
- `settings.py`: reads the theme's timings, pools and show hours.
- `radar.py`: puts ESPHome's separate radar values back together (ICD-002).
- `__main__.py`: the MQTT loop.
