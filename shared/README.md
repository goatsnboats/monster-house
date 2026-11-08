# shared/ — what every component agrees on

- `topics.py` — every MQTT topic name, written down once. Components import
  names from here; a test fails if a topic string appears anywhere else.

Payload formats (what goes *inside* each message) are not defined yet: TBD-003.

## How to use it

```python
from shared import topics

client.publish(topics.EYES_BLINK, ...)
client.subscribe(topics.EYES_STATUS_ALL)
topics.radar_target(1, "x")        # monster-radar/sensor/target_1_x/state
```

## Tests

```bash
.venv/bin/python -m pytest tests/test_topics.py
```
