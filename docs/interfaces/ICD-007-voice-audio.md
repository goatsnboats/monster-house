# ICD-007 — Voice audio

> **Status:** Skeleton · **Updated:** 2026-11-09 · **Requirements:** SHW-037, INF-005, VOC-001 · **Spec tree:** [N² chart](../requirements/spec-tree.md)

Falcon Player's audio leaves the porch Pi through a USB audio adapter (the Pi 5 has no
headphone jack) and reaches the amp as a line-level signal (architecture §3a, §6).

```yaml
id: ICD-007
title: Voice audio
status: skeleton
ends:
  - {component: falcon-player}
  - {component: porch-pi}
  - {component: usb-audio}
  - {component: amp}
medium: USB audio, then analog line level
```

## To be filled in
- **USB side:** a USB Audio Class adapter that Raspberry Pi OS sees as an ALSA device;
  it uses one of the porch Pi's 4 USB ports (INF-005, budget check).
- **Analog side:** line level, mono is fine (architecture §6); the cable runs from inside
  the front door to the amp, whose location is TBD-010.
- **Level:** FPP's volume cap and an operating-system cap (SHW-034), then the amp's gain
  (VOC-002), so the sidewalk level stays under TBD-026.
