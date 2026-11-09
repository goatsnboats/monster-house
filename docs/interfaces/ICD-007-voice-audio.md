# ICD-007 — Voice audio

> **Status:** Stub · **Plan:** A skeleton with TBDs at STOP 2. · **Spec tree:** [spec-tree.md](../requirements/spec-tree.md)

Falcon Player's audio leaves the porch Pi through the USB audio adapter and reaches the amp as a line-level signal.

```yaml
id: ICD-007
title: Voice audio
status: stub
ends:
  - {component: falcon-player}
  - {component: porch-pi}
  - {component: usb-audio}
  - {component: amp}
medium: USB audio, then analog line level
```
