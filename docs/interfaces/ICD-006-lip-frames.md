# ICD-006 — Lip light frames

> **Status:** Skeleton · **Updated:** 2026-11-09 · **Requirements:** SHW-036, MTH-005 · **Spec tree:** [N² chart](../requirements/spec-tree.md)

Falcon Player streams per-LED colors to the lip controller (WLED on the QuinLED
Dig-Quad) in time with the voice, using DDP (architecture §3a, §5).

```yaml
id: ICD-006
title: Lip light frames
status: skeleton
ends:
  - {component: falcon-player}
  - {component: lip-controller}
medium: DDP over Wi-Fi (UDP)
```

## To be filled in
- **Pixel layout:** upper lip, lower lip and extras as WLED segments 1–4 (MTH-003). LED
  counts depend on the porch lengths (TBD-007).
- **Frame rate:** the sequence's own, set in xLights.
- **Brightness:** capped in WLED (TBD-027), not in the sequence.
- **When the stream stops:** WLED falls back to its breathe effect (MTH-001); the idle
  color per theme is TBD-035.
