# ICD-003 — Clip commands and clip status

> **Status:** Stub · **Plan:** Written in full at STOP 2. · **Spec tree:** [spec-tree.md](../requirements/spec-tree.md)

The brain starts a voice-and-lips clip by playlist name; Falcon Player reports when it starts and finishes. Internal to Show control, but has its own ICD so the fake FPP (SIM) can be swapped for the real one.

```yaml
id: ICD-003
title: Clip commands and clip status
status: stub
ends:
  - {component: monster-brain}
  - {component: falcon-player}
medium: MQTT and/or HTTP (TBD-015)
```
