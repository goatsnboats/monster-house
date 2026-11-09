# `radar-esp32` — ESP32 dev board, network name monster-radar

> **Kind:** part · **Subsystem:** EAR (Ears) · **From stage:** 2 · **Data:** [components.yaml](../components.yaml)

ESP32 dev board in the radar box, network name `monster-radar`. Reads the LD2450 over serial and runs the radar firmware.

**Location:** radar-box, under the porch roof

## Software on it

| Software | From stage |
|---|---|
| `radar-firmware` | 2 |

## What it does

- read the radar
- run ESPHome
- publish over Wi-Fi

## Interfaces

- [ICD-009](../../interfaces/ICD-009-network.md): Network service

## Open items

- TBD-008 (porch Wi-Fi)

## Requirements

The requirements allocated to `radar-esp32` are listed in [trace.md](../../requirements/trace.md) (the matrix's "Allocated to" column).
