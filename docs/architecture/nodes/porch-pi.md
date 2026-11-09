# `porch-pi` — Raspberry Pi 5 with official supply, case with fan and 32 GB microSD

> **Kind:** part · **Subsystem:** INF (Infrastructure) · **From stage:** 3 · **Data:** [components.yaml](../components.yaml)

Raspberry Pi 5 just inside the front door, from Stage 3. Runs the brain, Mosquitto and Falcon Player, and feeds the USB audio adapter.

**Location:** shelf just inside the front door (TBD-010)

## Software on it

| Software | From stage |
|---|---|
| `falcon-player` | 3 |
| `monster-brain` | 3 |
| `mosquitto` | 3 |
| `phone-page` | 3 |
| `pi-setup` | 3 |
| `service-units` | 3 |
| `site-config` | 3 |
| `theme-halloween` | 3 |

## What it does

- host the Show control software
- provide the USB audio port

## Interfaces

- [ICD-007](../../interfaces/ICD-007-voice-audio.md): Voice audio
- [ICD-008](../../interfaces/ICD-008-power.md): Power
- [ICD-009](../../interfaces/ICD-009-network.md): Network service
- [ICD-013](../../interfaces/ICD-013-compute-platform.md): Compute platform

## Open items

- TBD-031 (memory size)
- TBD-036 (FPP alongside the brain)
- TBD-010 (exact place)

## Requirements

The requirements allocated to `porch-pi` are listed in [trace.md](../../requirements/trace.md) (the matrix's "Allocated to" column).
