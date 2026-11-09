# `lip-controller` — QuinLED Dig-Quad with WLED, network name monster-lips

> **Kind:** part · **Subsystem:** MTH (Mouth) · **From stage:** 4 · **Data:** [components.yaml](../components.yaml)

QuinLED Dig-Quad in the lip box, network name `monster-lips`. Runs WLED and drives the lip strips.

**Location:** lip-box on the porch

## Software on it

| Software | From stage |
|---|---|
| `wled` | 4 |

## What it does

- drive up to 4 LED outputs
- receive DDP frames over Wi-Fi

## Interfaces

- [ICD-006](../../interfaces/ICD-006-lip-frames.md): Lip light frames
- [ICD-009](../../interfaces/ICD-009-network.md): Network service

## Open items

- TBD-008 (porch Wi-Fi)
- TBD-033 (power)

## Requirements

The requirements allocated to `lip-controller` are listed in [trace.md](../../requirements/trace.md) (the matrix's "Allocated to" column).
