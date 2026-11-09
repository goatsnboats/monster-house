# ICD-013 — Compute platform

> **Status:** Draft (partial: Pi details wait for hardware, TBD-013) · **Updated:** 2026-11-09 · **Requirements:** INF-001, INF-002, EYE-018, SHW-029 · **Spec tree:** [N² chart](../requirements/spec-tree.md)

What a computer in INF gives the software that runs on it. The desktop (DEV) stands in
for the Pis in Stages 0–2 under the same rules, so the code that runs there runs on a Pi
unchanged (SYS-039).

```yaml
id: ICD-013
title: Compute platform
status: draft
ends:
  - {component: eye-pi-left}
  - {component: eye-pi-right}
  - {component: porch-pi}
  - {component: eye-renderer}
  - {component: monster-brain}
  - {component: falcon-player}
  - {component: mosquitto}
medium: Operating system and runtime
```

## What every host provides

| | Eye Pis (`eye-pi-left`, `eye-pi-right`) | Porch Pi (`porch-pi`) | Desktop, Stages 0–2 |
|---|---|---|---|
| Hardware | Raspberry Pi 5, 1GB | Raspberry Pi 5, RAM TBD-031 | Owner's desktop |
| Operating system | Raspberry Pi OS Lite, 64-bit (Bookworm) | Raspberry Pi OS Lite, 64-bit (Bookworm); FPP's own image instead? TBD-036 | Ubuntu 26.04 |
| Python | 3.11 (Bookworm's) | 3.11 | 3.11 in `.venv` (via `uv`) |
| Graphics | OpenGL ES 3.0 or later; full-screen KMS/DRM through SDL, no desktop environment (ADR 0002; untested on a Pi: TBD-013) | — | Desktop window |
| Audio | — | ALSA device for the USB audio adapter (ICD-007) | Desktop speakers (fake FPP) |
| Services | systemd starts the renderer at boot (DEP-002) | systemd starts the brain, Mosquitto, FPP | Started by hand |
| Network | Wi-Fi, name `eye-left` / `eye-right` (ICD-009) | Wi-Fi, name `monster-brain` | Home network |

## Capacities (for the budget check)

Each host's capacity is its `provides` in `docs/architecture/components.yaml`; each
program's use is its `needs`. `tools/reqs/budget.py` adds them up per stage, and the
result is in [trace.md](../requirements/trace.md#budgets). Known so far:

- Eye Pi memory: 1024 MB (architecture §2). The eye renderer peaked at 153 MB at 60 fps
  on the desktop (TS-002); the Pi figure and the operating system's share are TBD-032.
- Porch Pi memory: TBD-031; the programs' needs: TBD-032.
- Porch Pi USB ports: 4; the USB audio adapter uses 1.

## Rules for software that runs here

- Plain Python 3.11 with pinned dependencies (`requirements.txt`); no desktop-only
  dependencies (architecture §3).
- Settings come from files: the site config ([ICD-015](ICD-015-site-config.md)) and the
  theme ([ICD-005](ICD-005-theme-folder.md)).
- Shaders are GLSL ES 3.00 (SYS-040).
