# sim/ — simulators

Desktop stand-ins for hardware, sending and receiving *exactly* the same MQTT
messages as the real thing:
- **fake radar** (drag pretend visitors; mimics ESPHome's LD2450 topics). Step 3, done
- fake Falcon Player (logs clip triggers, plays placeholder audio). Step 4
- house preview (eyes composited onto the house photo). Step 5

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

**See the eyes follow a kid** (Step 3's "done when"): run these in four terminals.

```bash
.venv/bin/python -m eyes --side left
.venv/bin/python -m eyes --side right
.venv/bin/python -m brain              # placeholder: look at the closest kid
.venv/bin/python -m sim.fake_radar
```

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
