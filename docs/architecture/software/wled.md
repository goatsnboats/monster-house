# `wled` — WLED firmware and its settings (segments, fallback breathe effect, brightness limit)

> **Kind:** software · **Subsystem:** MTH (Mouth) · **From stage:** 4 · **Data:** [components.yaml](../components.yaml)

WLED firmware on the lip controller and its settings: segments, the fallback breathe effect, the brightness limit.

## Where it runs

| From stage | Runs on |
|---|---|
| 4 | `lip-controller` |

## What it does

- show DDP frames while FPP streams
- fall back to a slow breathe when it stops
- cap brightness

## Interfaces

- None.

## Open items

- TBD-027 (brightness cap)
- TBD-035 (idle color per theme)

## Requirements

The requirements allocated to `wled` are listed in [trace.md](../../requirements/trace.md) (the matrix's "Allocated to" column).
