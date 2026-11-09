# `eye-pi-right` — Raspberry Pi 5 (1GB) with supply and microSD, right (large) window's eye pod

> **Kind:** part · **Subsystem:** INF (Infrastructure) · **From stage:** 1 · **Data:** [components.yaml](../components.yaml)

Raspberry Pi 5 (1GB) in the right eye pod, behind the larger window. Same as the left one.

**Location:** bedroom, right eye pod

## Software on it

| Software | From stage |
|---|---|
| `eye-renderer` | 1 |
| `pi-setup` | 1 |
| `pi-setup` | 3 |
| `service-units` | 1 |
| `service-units` | 3 |
| `site-config` | 1 |
| `site-config` | 3 |
| `theme-halloween` | 1 |
| `theme-halloween` | 3 |

## What it does

- host eye-renderer full-screen on KMS/DRM
- output video to the projector

## Interfaces

- [ICD-009](../../interfaces/ICD-009-network.md): Network service
- [ICD-013](../../interfaces/ICD-013-compute-platform.md): Compute platform
- [ICD-014](../../interfaces/ICD-014-eye-video.md): Eye video

## Open items

- TBD-013
- TBD-032 (memory)

## Requirements

The requirements allocated to `eye-pi-right` are listed in [trace.md](../../requirements/trace.md) (the matrix's "Allocated to" column).
