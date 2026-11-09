# `house-preview` — House preview (live eyes on the house photo, plus a lip line)

> **Kind:** software · **Subsystem:** SIM (Simulators) · **From stage:** 0 · **Data:** [components.yaml](../components.yaml)

The live eyes on a photo of the house, plus a lip line, for deciding the look. Listens to the eye commands like a third eye. Code in `sim/`.

## Where it runs

| From stage | Runs on |
|---|---|
| 0 | `desktop` |

## What it does

- composite both eyes onto docs/reference/house-front.jpg
- draw a lip line

## Interfaces

- [ICD-001](../../interfaces/ICD-001-eye-commands.md): Eye commands and eye status

## Open items

- TBD-004 (lopsided or matched)

## Requirements

The requirements allocated to `house-preview` are listed in [trace.md](../../requirements/trace.md) (the matrix's "Allocated to" column).
