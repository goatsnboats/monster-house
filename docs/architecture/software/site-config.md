# `site-config` — Site configuration file (the house's own settings, the same for every theme)

> **Kind:** software · **Subsystem:** INF (Infrastructure) · **From stage:** 0 · **Data:** [components.yaml](../components.yaml)

The house's own settings file, `config/site.yaml`: positions, window settings, zones. The same for every theme.

## Where it runs

| From stage | Runs on |
|---|---|
| 0 | `desktop` |
| 1 | `desktop`, `eye-pi-left`, `eye-pi-right` |
| 3 | `porch-pi`, `eye-pi-left`, `eye-pi-right` |

## What it does

- hold eye and radar positions in house coordinates
- hold each eye's window settings
- hold network names

## Interfaces

- [ICD-015](../../interfaces/ICD-015-site-config.md): Site config

## Open items

- TBD-006, TBD-018, TBD-029 (measurements)

## Requirements

The requirements allocated to `site-config` are listed in [trace.md](../../requirements/trace.md) (the matrix's "Allocated to" column).
