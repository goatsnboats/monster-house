# `mosquitto` — Mosquitto MQTT broker, third-party, with our config (deploy/mosquitto/)

> **Kind:** software · **Subsystem:** SHW (Show control) · **From stage:** 0 · **Data:** [components.yaml](../components.yaml)

Third-party MQTT broker that every MQTT message passes through, with retained and last-will messages. Our config is in `deploy/mosquitto/`.

## Where it runs

| From stage | Runs on |
|---|---|
| 0 | `desktop` |
| 3 | `porch-pi` |

## What it does

- pass every MQTT message between components
- hold retained messages
- deliver last-will messages

## Interfaces

- [ICD-013](../../interfaces/ICD-013-compute-platform.md): Compute platform

## Requirements

The requirements allocated to `mosquitto` are listed in [trace.md](../../requirements/trace.md) (the matrix's "Allocated to" column).
