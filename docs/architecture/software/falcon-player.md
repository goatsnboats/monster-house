# `falcon-player` — Falcon Player (FPP), third-party; faked by fake-fpp in Stages 0-2

> **Kind:** software · **Subsystem:** SHW (Show control) · **From stage:** 3 · **Data:** [components.yaml](../components.yaml)

Third-party show player (FPP). Plays each voice clip and its lip sequence together and streams the lip frames. Not used until Stage 3; `fake-fpp` stands in.

## Where it runs

| From stage | Runs on |
|---|---|
| 3 | `porch-pi` |

## What it does

- play a voice clip and its lip sequence together
- run the show schedule
- send lip frames over DDP
- report clip status

## Interfaces

- [ICD-003](../../interfaces/ICD-003-clips.md): Clip commands and clip status
- [ICD-006](../../interfaces/ICD-006-lip-frames.md): Lip light frames
- [ICD-007](../../interfaces/ICD-007-voice-audio.md): Voice audio
- [ICD-012](../../interfaces/ICD-012-sequence-upload.md): Sequence and audio upload
- [ICD-013](../../interfaces/ICD-013-compute-platform.md): Compute platform

## Open items

- TBD-015 (exact topics)
- TBD-036 (on the porch Pi with the brain?)
- TBD-022 (start delay)

## Requirements

The requirements allocated to `falcon-player` are listed in [trace.md](../../requirements/trace.md) (the matrix's "Allocated to" column).
