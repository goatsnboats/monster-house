# sim/ — simulators

Desktop stand-ins for hardware, sending and receiving *exactly* the same MQTT
messages as the real thing:
- **fake radar** (drag pretend visitors; mimics ESPHome's LD2450 topics). Step 3, done
- **fake Falcon Player** (logs clip triggers, answers playing/idle, plays the theme's audio). Step 4, done
- **pretend visit** (a scripted visit with the real brain, no windows). Step 4, done
- **house preview** (the live eyes and the lips on the house photo). Step 5, done

## Fake radar

A top-down view of the front of the house: house and porch at the top, steps and walk
in the middle, sidewalk and street at the bottom. Right on the screen is right as seen
from the street. The yellow fan is what the radar can see (6 m, 60° each side), and the
red box is its blind spot by the door. Up to 3 pretend kids; a kid the radar can't see
is drawn hollow. Requirements SIM-001 to SIM-003; messages in
[ICD-002](../docs/interfaces/ICD-002-radar-targets.md).

### How to run it

With the broker running (see `deploy/mosquitto/README.md`), from the repository root:

```bash
.venv/bin/python -m sim.fake_radar
```

| Do this | To |
|---|---|
| Click empty ground | Add a kid there (up to 3) |
| Drag a kid | Move them |
| Right-click a kid | Remove them |
| `a` | Add a kid on the sidewalk |
| `Delete` / `Backspace`, `c` | Remove the last kid, remove them all |
| `Esc` | Quit (it says "offline" as it goes) |

The panel at the bottom shows the last value sent for each slot. Options: `--no-mqtt`
(don't connect), `--host`/`--port`, `--screenshot file.png` (one frame with example kids,
no window needed).

**See a pretend visit:** run the eyes, the fake FPP, the brain and the fake radar
(commands in `brain/README.md`), then drag a kid up the path. The monster wakes only
for a kid coming toward the house.

Watch the raw messages with `.venv/bin/python -m shared.mqtt_tool sub radar`.

### What it sends, like the real radar

From ESPHome's source (ICD-002): `monster-radar/sensor/target_{1-3}_{x,y,speed}/state`
in whole mm and mm/s relative to the radar, plus `target_count`, all retained. Speed is
negative toward the radar. A value goes out only when it changes, and once more a frame
later. A slot that empties sends `nan`. About 10 frames a second. `monster-radar/status`
is `online`, with `offline` as the last-will. When a kid leaves, the others keep their
slots; a new kid takes the lowest free slot.

### Settings

- `sim/fake_radar.yaml`: the drawing (walk, steps, porch, sidewalk; rough guesses from
  the house photo), frames per second, an optional `jitter_mm` wobble, and the speed window.
- `config/site.yaml` (ICD-015): where the radar is (`radar.mount`) and its blind spot by
  the door (`radar.door_zone_mm`, a guess until measured, TBD-029). The brain reads the
  same file.

### Code

- `radar_model.py`: kids in, ESPHome messages out. No window, so it's easy to test.
- `fake_radar.py`: the window, the mouse and the MQTT connection.

## Fake Falcon Player

Takes the brain's clip starts and answers as Falcon Player will (ICD-003, SIM-004):
`playing` and the clip's name, then `idle` when it ends. A clip lasts as long as
`themes/<theme>/audio/<clip>.wav`, or `--clip-seconds` (3 s) while there's no recording.

```bash
.venv/bin/python -m sim.fake_fpp            # --sound plays the .wav files (paplay or aplay)
```

## Pretend visit

```bash
.venv/bin/python -m sim.pretend_visit
```

Plays a scripted visit (a kid walks up, goes to the door, walks away) through the real
brain, the radar model and the fake FPP on a pretend clock, and prints every mood,
expression, clip and blink. The tests and `tools/results/stage_0_step_4.py` use it too.

## House preview

The live eyes on `docs/reference/house-front.jpg`, at the two windows, with the lips'
glowing line, for judging lopsided vs matched eyes, eye size and colors (SIM-005).
It listens to the brain like a third eye (ICD-001, SIM-006) but never reports itself
as one. Each eye is drawn by the real eye renderer and warped onto its window.

```bash
.venv/bin/python -m sim.house_preview                # --no-mqtt: just wander
```

| Do this | To |
|---|---|
| Drag a corner or a lip point | Move it |
| `m` | Eye mode: fills each window (lopsided) · ovals as big as each window · matched ovals (both the small window's size, in meters) · ovals stretched to each window |
| `c` | Next iris color (`iris_colors` in the layout file) |
| `d` | Dusk: dim the photo (the eyes are lit) |
| `p`, `l`, `h` | Window panes on/off (set in the layout file), lips on/off, handles on/off |
| `s` | Save the corners and lip points to `sim/house_preview.yaml` |
| `Space`, `1`-`6`, `i` | Blink, expressions, wander (when no brain is running) |

The window title shows the mode, color and dusk level. Run it with the brain and the
fake radar (see `brain/README.md`) to watch a whole pretend visit on the house.
`--screenshot file.png` draws one frame without a window.
