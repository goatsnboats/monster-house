# `eye-renderer` — Eye renderer (Python + moderngl + pygame-ce, ADR 0002)

> **Kind:** software · **Subsystem:** EYE (Eyes) · **From stage:** 0 · **Data:** [components.yaml](../components.yaml)

Draws one big cartoon eye per window on the GPU and obeys the brain's eye commands. It is the same code in a desktop window (Stage 0) and full-screen on an eye Pi (Stage 1 on). See [ADR 0002](../../decisions/0002-eye-renderer.md) and `eyes/`.

## Where it runs

| From stage | Runs on |
|---|---|
| 0 | `desktop` |
| 1 | `eye-pi-left`, `eye-pi-right` |

## What it does

- draw the layered eye on the GPU (OpenGL ES 3.0 / GLSL ES 3.00)
- ease between expressions
- glide the pupil toward a look point, computed from its own window's position
- blink on command, with a fallback blink timer
- apply per-eye window settings (size, placement, rotation, mirroring, brightness)
- publish its online/offline status

## Interfaces

- [ICD-001](../../interfaces/ICD-001-eye-commands.md): Eye commands and eye status
- [ICD-005](../../interfaces/ICD-005-theme-folder.md): Theme folder
- [ICD-013](../../interfaces/ICD-013-compute-platform.md): Compute platform
- [ICD-015](../../interfaces/ICD-015-site-config.md): Site config

## Open items

- TBD-013 (untested on a real Pi)
- TBD-004 (lopsided or matched eyes)
- TBD-023 (fallback timer)

## Requirements

The requirements allocated to `eye-renderer` are listed in [trace.md](../../requirements/trace.md) (the matrix's "Allocated to" column).
