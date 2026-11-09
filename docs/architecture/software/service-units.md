# `service-units` — System service files (start at boot)

> **Kind:** software · **Subsystem:** DEP (Deployment) · **From stage:** 1 · **Data:** [components.yaml](../components.yaml)

systemd service files that start the renderer, brain and broker at boot and restart them if they stop.

## Where it runs

| From stage | Runs on |
|---|---|
| 1 | `eye-pi-left`, `eye-pi-right` |
| 3 | `porch-pi`, `eye-pi-left`, `eye-pi-right` |

## What it does

- start the renderer
- brain and broker at boot and restart them if they stop

## Interfaces

- None.

## Requirements

The requirements allocated to `service-units` are listed in [trace.md](../../requirements/trace.md) (the matrix's "Allocated to" column).
