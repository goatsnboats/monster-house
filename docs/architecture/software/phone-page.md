# `phone-page` — Phone page served by the brain on the home network

> **Kind:** software · **Subsystem:** SHW (Show control) · **From stage:** 0 · **Data:** [components.yaml](../components.yaml)

A small web page, served by the brain, with the owner's buttons and the current mood. Part of `brain/`.

## Where it runs

| From stage | Runs on |
|---|---|
| 0 | `desktop` |
| 3 | `porch-pi` |

## What it does

- show buttons (great costume
- burp
- sing
- mute voice
- sleep now
- wake now)
- show the current mood
- choose a theme

## Interfaces

- [ICD-004](../../interfaces/ICD-004-phone-page.md): Phone buttons and current mood

## Requirements

The requirements allocated to `phone-page` are listed in [trace.md](../../requirements/trace.md) (the matrix's "Allocated to" column).
