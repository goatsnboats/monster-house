# `monster-brain` — Monster brain (Python service)

> **Kind:** software · **Subsystem:** SHW (Show control) · **From stage:** 0 · **Data:** [components.yaml](../components.yaml)

The one place that decides: moods, gaze, blinks, clips, coming and going, failures. It also serves the phone page. Code in `brain/`.

## Where it runs

| From stage | Runs on |
|---|---|
| 0 | `desktop` |
| 3 | `porch-pi` |

## What it does

- run the mood state machine (Asleep, Waking, Greeting, Watching, Goodbye)
- turn radar positions into a look point and choose the focus visitor
- own blinks for both eyes
- pick clips from the theme's pools and trigger them
- handle failures so the monster looks sleepy, never broken

## Interfaces

- [ICD-001](../../interfaces/ICD-001-eye-commands.md): Eye commands and eye status
- [ICD-002](../../interfaces/ICD-002-radar-targets.md): Radar targets
- [ICD-003](../../interfaces/ICD-003-clips.md): Clip commands and clip status
- [ICD-004](../../interfaces/ICD-004-phone-page.md): Phone buttons and current mood
- [ICD-005](../../interfaces/ICD-005-theme-folder.md): Theme folder
- [ICD-013](../../interfaces/ICD-013-compute-platform.md): Compute platform
- [ICD-015](../../interfaces/ICD-015-site-config.md): Site config

## Open items

- TBD-020, TBD-021, TBD-034 (timing)
- TBD-028 (door hold)
- TBD-030 (coming vs going)

## Requirements

The requirements allocated to `monster-brain` are listed in [trace.md](../../requirements/trace.md) (the matrix's "Allocated to" column).
