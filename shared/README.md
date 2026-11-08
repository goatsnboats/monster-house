# shared/ — what every component agrees on

- `topics.py` — every MQTT topic name, written down once. Components import
  names from here; a test fails if a topic string appears anywhere else.
- `mqtt_client.py` — broker address defaults and a client factory (paho-mqtt 2.x).
- `mqtt_tool.py` — command-line publish/subscribe tool for debugging.

Payload formats (what goes *inside* each message) are not defined yet: TBD-003.

## How to use it

```python
from shared import topics

client.publish(topics.EYES_BLINK, ...)
client.subscribe(topics.EYES_STATUS_ALL)
topics.radar_target(1, "x")        # monster-radar/sensor/target_1_x/state
```

## Debug tool

Needs the broker running (`deploy/mosquitto/run-dev.sh`). From the repo root:

```bash
.venv/bin/python -m shared.mqtt_tool topics                  # short names -> topics
.venv/bin/python -m shared.mqtt_tool sub                     # watch everything under monster/
.venv/bin/python -m shared.mqtt_tool sub eye-status radar    # or pick topics
.venv/bin/python -m shared.mqtt_tool pub blink '{"ms": 180}' # payload sent exactly as typed
.venv/bin/python -m shared.mqtt_tool pub state asleep --retain
```

`sub` also takes `--count N` (stop after N messages) and `--timeout S`.
Both take `--host` / `--port` (default `localhost:1883`).

## Tests

```bash
.venv/bin/python -m pytest tests/test_topics.py tests/test_mqtt_tool.py
```
