# shared/ — what every component agrees on

- `topics.py` — every MQTT topic name, written down once. Components import
  names from here; a test fails if a topic string appears anywhere else.
- `mqtt_client.py` — broker address defaults and a client factory (paho-mqtt 2.x).
- `mqtt_tool.py` — command-line publish/subscribe tool for debugging.
- `messages/` — what goes *inside* each message: one module per ICD, **generated from
  the ICDs** by the checker ([ADR 0003](../docs/decisions/0003-message-schemas.md)).
  Only `messages/codec.py` and `messages/__init__.py` are written by hand.
- `schema.py` — the small JSON-Schema checker every payload is checked with (the
  checker uses it on the ICD examples too).

## How to use it

```python
from shared import topics

client.publish(topics.EYES_BLINK, ...)
client.subscribe(topics.EYES_STATUS_ALL)
topics.radar_target(1, "x")        # monster-radar/sensor/target_1_x/state
```

## Sending and receiving messages

```python
from shared import topics
from shared.messages import eye_commands as eyes

client.publish(topics.EYES_BLINK, eyes.encode("blink", eyes.Blink(ms=180)))   # b'{"ms": 180}'

def on_message(client, userdata, msg):
    blink = eyes.decode("blink", msg.payload)   # Blink(ms=180), or None if the payload is bad
```

- `decode()` never raises. A payload that breaks the ICD is logged (`dropped ICD-001
  blink: ...`) and returns `None`, so the component carries on (fail friendly).
- `encode()` raises `ValueError` for a message that breaks the ICD: a bug in our code.
- JSON objects (commands) become dataclasses; plain-text payloads (eye status, radar
  numbers) stay strings.

**To change a message:** edit its ICD in `docs/interfaces/`, then run
`.venv/bin/python -m tools.reqs.check`. That rewrites `messages/`. Never edit the
generated modules; a test fails if they don't match the ICDs. A `oneOf` (a message
with alternative shapes, like `look`) needs a `title` on each choice: it becomes the
class name.

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
.venv/bin/python -m pytest tests/test_topics.py tests/test_mqtt_tool.py tests/test_messages.py
```
