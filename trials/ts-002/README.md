# TS-002 trial: the same minimal eye, two ways

Throwaway code for [TS-002](../../docs/trades/TS-002-eye-renderer.md). Nothing outside
this folder imports it.

- `a/`: Python + `moderngl` + `pygame-ce` (`eye.py`, shader `eye.frag`)
- `b/`: Godot 4.7.2 project (`eye.gd`, `mini_mqtt.gd`, shader `eye.gdshader`)
- `results/`: screenshots (`compare-a-top-b-bottom.png`: A on top, B below)
- `measure.sh`: runs a command and samples its CPU and memory from 5 s to 25 s (first, hand-run session)
- `run_trials.py`: repeats every measurement and writes logs, frame timings, screenshots and `results.json`
- `score.py`: weighted totals and sensitivity
- `make_figures.py`: the results report's figures
- `probes/`: `gl_probe.py` (moderngl at the Pi's OpenGL level) and `readback_probe.py` (RGB vs RGBA)

The report built from these is in
[docs/trades/results/TS-002](../../docs/trades/results/TS-002/README.md).

## Set up (desktop)

```bash
uv venv --python 3.11 trials/ts-002/.venv
uv pip install --python trials/ts-002/.venv/bin/python moderngl==5.13.0 pygame-ce==2.5.8 paho-mqtt==2.2.0 PyYAML==6.0.3
# Godot: unzip Godot_v4.7.2-stable_linux.x86_64.zip from godotengine.org into trials/ts-002/godot/
```

## Run

```bash
trials/ts-002/.venv/bin/python trials/ts-002/a/eye.py            # option A
trials/ts-002/godot/Godot_v4.7.2-stable_linux.x86_64 --path trials/ts-002/b   # option B
```

Both take the same options (Godot's after a `--`): `--mirror`, `--rotate90`,
`--expression happy`, `--bench 60` (cycle expressions, then print frame timing),
`--fps-cap 60`, `--no-vsync`, `--frame-log file.txt`, `--screenshot file.png`, `--mqtt` (needs the broker).
Keys: 1–6 expressions, space blinks, Esc quits. The mouse moves the gaze.
Option A also takes `--gles` (ask for an OpenGL ES 3.0 context, like the Pi).
