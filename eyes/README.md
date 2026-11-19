# eyes/ — the eye renderer

Draws one monster eye per window on the GPU (Python + moderngl + pygame-ce,
[ADR 0002](../docs/decisions/0002-eye-renderer.md)), matching
`docs/reference/eye-sketch.html`. Stage 0 Step 2. Requirements EYE-001 to EYE-018.

**Status:** draws the eye with every expression, eases between them, blinks, glides the
pupil to a look point with parallax, wanders and blinks on its own, and applies each
window's settings. **Not yet:** the MQTT listener and online/offline status (waits for
TS-003, how messages are defined in code), theme switching while running, full-screen
on the Pi (Step 8).

## How to run it

From the repository root, with the virtual environment set up (see the main README):

```bash
.venv/bin/python -m eyes --side left        # the small window
.venv/bin/python -m eyes --side right       # the big window (run both for two eyes)
```

Keys: `1`-`6` neutral, happy, sparkle, surprised, sleepy, asleep · `space` blink ·
`i` look around on its own · mouse: look at the mouse · `Esc` quit. Left alone, the eye
wanders and blinks by itself, as it will when the brain goes quiet.

Useful options:

| Option | What it does |
|---|---|
| `--projector` | Show exactly what the projector gets: turned a quarter turn if `rotate_deg: 90`, and mirrored. Without it you see the street view |
| `--long-side 900` | Window size: pixels along the window's long side |
| `--shape stretch` | Eye shape to try: `oval` (the sketch, default), `stretch` (oval shaped like the window), `window` (fills the glass). A trial option until the owner picks; then it becomes a site-config setting |
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
| `__main__.py` | The window, keys and mouse |

Tests: `tests/test_eyes.py` (the drawing tests use Mesa's CPU renderer, so they need no GPU).
