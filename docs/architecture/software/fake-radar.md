# `fake-radar` — Fake radar (drag up to 3 pretend visitors)

> **Kind:** software · **Subsystem:** SIM (Simulators) · **From stage:** 0 · **Data:** [components.yaml](../components.yaml)

A desktop window with a top-down view of the walk where the owner drags pretend visitors; publishes exactly what the radar would, including a blind spot by the door. Code in `sim/`.

## Where it runs

| From stage | Runs on |
|---|---|
| 0 | `desktop` |

## What it does

- publish exactly the topics and units the real radar does

## Interfaces

- [ICD-002](../../interfaces/ICD-002-radar-targets.md): Radar targets

## Open items

- TBD-029 (blind spot size)
- TBD-030 (direction)

## Requirements

The requirements allocated to `fake-radar` are listed in [trace.md](../../requirements/trace.md) (the matrix's "Allocated to" column).
