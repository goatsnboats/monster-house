# `fake-fpp` — Fake Falcon Player

> **Kind:** software · **Subsystem:** SIM (Simulators) · **From stage:** 0 · **Data:** [components.yaml](../components.yaml)

Stands in for Falcon Player in Stages 0–2: logs clip triggers, plays placeholder audio, reports playing and idle. Code in `sim/`.

## Where it runs

| From stage | Runs on |
|---|---|
| 0 | `desktop` |

## What it does

- log clip triggers
- play placeholder audio
- report clip finished like FPP

## Interfaces

- [ICD-003](../../interfaces/ICD-003-clips.md): Clip commands and clip status

## Open items

- TBD-015 (match FPP's real topics)

## Requirements

The requirements allocated to `fake-fpp` are listed in [trace.md](../../requirements/trace.md) (the matrix's "Allocated to" column).
