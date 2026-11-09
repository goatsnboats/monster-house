# `radar-firmware` — Our ESPHome configuration (esphome/)

> **Kind:** software · **Subsystem:** EAR (Ears) · **From stage:** 2 · **Data:** [components.yaml](../components.yaml)

Our ESPHome configuration for the radar node (`esphome/`, Stage 2): sensors named to match `shared/topics.py`, about 10 updates per second, filter zones.

## Where it runs

| From stage | Runs on |
|---|---|
| 2 | `radar-esp32` |

## What it does

- expose X
- Y and speed per target
- a target count and the approach zone
- publish them over MQTT at about 10 per second

## Interfaces

- [ICD-002](../../interfaces/ICD-002-radar-targets.md): Radar targets

## Open items

- TBD-030 (direction, payload format)
- TBD-016 (range to the sidewalk)

## Requirements

The requirements allocated to `radar-firmware` are listed in [trace.md](../../requirements/trace.md) (the matrix's "Allocated to" column).
