# `pi-setup` — Pi setup scripts (deploy/)

> **Kind:** software · **Subsystem:** DEP (Deployment) · **From stage:** 0 · **Data:** [components.yaml](../components.yaml)

Scripts in `deploy/` that turn a fresh Raspberry Pi OS Lite install into an eye pod or the porch Pi (Stage 0 Step 8).

## Where it runs

| From stage | Runs on |
|---|---|
| 1 | `eye-pi-left`, `eye-pi-right` |
| 3 | `porch-pi`, `eye-pi-left`, `eye-pi-right` |

## What it does

- turn a fresh Raspberry Pi OS Lite (64-bit) install into an eye pod or the porch Pi

## Interfaces

- None.

## Open items

- TBD-036 (porch Pi with FPP)

## Requirements

The requirements allocated to `pi-setup` are listed in [trace.md](../../requirements/trace.md) (the matrix's "Allocated to" column).
