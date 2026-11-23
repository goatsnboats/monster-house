# eyes/ — the eye renderer

Draws one monster eye per window on the GPU (Python + moderngl + pygame-ce,
[ADR 0002](../docs/decisions/0002-eye-renderer.md)), matching
`docs/reference/eye-sketch.html`. Stage 0 Step 2. Requirements EYE-001 to EYE-018.

**Status:** draws the eye with every expression, eases between them, blinks, glides the
pupil to a look point with parallax, wanders and blinks on its own, and applies each
window's settings. It obeys the brain's MQTT messages (ICD-001), switches theme while
running, and announces itself online/offline. **Not yet:** 60 fps measured in a real
window, full-screen on the Pi (Step 8).

## How to run it

From the repository root, with the virtual environment set up (see the main README) and
the broker running (see `deploy/mosquitto/README.md`):

```bash
.venv/bin/python -m eyes --side left        # the small window
.venv/bin/python -m eyes --side right       # the big window (run both for two eyes)
```

No broker? The eye still runs, wanders and blinks on its own, and connects when the
broker appears.

## Talking to it over MQTT

Until the brain exists, play the brain from another terminal (ICD-001 has every message):

```bash
.venv/bin/python -m shared.mqtt_tool pub look '{"x": 1.2, "y": 3.5, "z": 1.0}'   # look at a point (m, house coordinates)
.venv/bin/python -m shared.mqtt_tool pub look '{"mode": "idle"}'                  # wander
.venv/bin/python -m shared.mqtt_tool pub expression '{"name": "happy", "ms": 300}'
.venv/bin/python -m shared.mqtt_tool pub blink '{"ms": 180}'                       # both eyes blink
.venv/bin/python -m shared.mqtt_tool pub theme '{"name": "halloween"}' --retain
.venv/bin/python -m shared.mqtt_tool sub eye-status                                # online / offline
```

A message that breaks ICD-001 is logged (`dropped ICD-001 blink: ...`) and ignored; the
screen never shows it. After 5 s with no brain messages (TBD-023) the eye looks after
itself again. A theme kept by the broker (retained) doesn't count as the brain being there.

Keys: `1`-`6` neutral, happy, sparkle, surprised, sleepy, asleep · `space` blink ·
`i` look around on its own · mouse: look at the mouse · `Esc` quit. Left alone, the eye
wanders and blinks by itself, as it will when the brain goes quiet.

Useful options:

| Option | What it does |
|---|---|
| `--host`, `--port` | The MQTT broker (default `localhost:1883`) |
| `--no-mqtt` | Don't connect: keyboard and mouse only |
| `--projector` | Show exactly what the projector gets: turned a quarter turn if `rotate_deg: 90`, and mirrored. Without it you see the street view |
| `--long-side 900` | Window size: pixels along the window's long side |
| `--shape oval` | Try another eye shape for this run. The setting itself is `eye_shape` in `config/site.yaml`, per eye: `square` (the white fills the glass, the default), `oval` (the sketch) or `stretch` (an oval shaped like the window) |
| `--fullscreen` | Full screen with the cursor hidden, as on the Pi |
| `--seconds 20 --no-vsync` | Quit after 20 s and print frame timing (60 fps check, EYE-008) |
| `--screenshot eye.png --software` | Draw one frame to a PNG with no window and no GPU |

## Where its settings come from

- **The window:** `config/site.yaml`, `eyes.left` / `eyes.right` (ICD-015): position on
  the house, glass size, rotation, mirroring, where the eye sits, brightness.
- **Colors and blink timing:** `themes/<theme>/settings.yaml` (ICD-005). Only the iris
  and sclera colors come from the theme today; the lids, ring, pupil and outline use the
  sketch's colors.

## How it is built

| File | Holds |
|---|---|
| `expressions.py` | The expression table (architecture §2) |
| `gaze.py` | Look point on the house → iris position, per eye |
| `state.py` | Easing, blinks, gliding, wandering and the fallback timer (no drawing) |
| `config.py` | Reading the site config and the theme |
| `render.py`, `shaders/eye.frag` | The drawing: one shader, all on the GPU |
| `link.py` | MQTT: the brain's messages in (checked by `shared/messages`), online/offline out |
| `__main__.py` | The window, keys and mouse |

Tests: `tests/test_eyes.py` (the drawing tests use Mesa's CPU renderer, so they need no
GPU) and `tests/test_eye_link.py` (the MQTT side; two of them need the broker running,
and they publish to the real `monster/eyes/<side>/status` topics, leaving them
`offline`: don't run them while the eyes are up).
