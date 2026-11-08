# monster-house

A friendly animated monster face on the house. Start with `CLAUDE.md` and
`docs/architecture.md`; the current work plan is `docs/stage-0-plan.md`.

## One-time setup (desktop or Raspberry Pi OS)

Python 3.11 is the target (it's what Raspberry Pi OS Bookworm ships).

**On the Ubuntu desktop** (its system Python is newer, so let `uv` fetch 3.11):

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

**On a Pi (Bookworm)**, plain `venv` is enough:

```bash
sudo apt install python3-venv
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Every dependency is pinned in `requirements.txt`.

## Run the tests

```bash
.venv/bin/python -m pytest
```

The two tests in `tests/test_mqtt_integration.py` need the broker running;
without it they are **skipped** (shown as `s`), not failed.

## See a message travel through the broker

1. One-time: `sudo apt install mosquitto mosquitto-clients`, then
   `sudo systemctl disable --now mosquitto` (see `deploy/mosquitto/README.md`).
2. Terminal 1, the broker: `deploy/mosquitto/run-dev.sh`
3. Terminal 2, a listener: `.venv/bin/python -m shared.mqtt_tool sub`
4. Terminal 3, a sender: `.venv/bin/python -m shared.mqtt_tool pub test '{"hello": "monster"}'`

Terminal 2 prints `monster/debug/test {"hello": "monster"}`.
More on the debug tool in `shared/README.md`.

## Folders

| Folder | What's in it |
|---|---|
| `brain/` | Monster brain: moods, gaze, clip pools, phone page |
| `eyes/` | Eye renderer (GPU) |
| `sim/` | Fake radar, fake Falcon Player, house preview |
| `shared/` | MQTT topic names and helpers used by everything |
| `esphome/` | Radar (ESP32 + LD2450) config |
| `xlights/` | Lip models and sequences |
| `themes/` | Per-holiday settings, art, audio |
| `deploy/` | Broker config, Pi setup scripts, services |
| `docs/` | Architecture, plans, decisions |
| `tests/` | `pytest` tests |
