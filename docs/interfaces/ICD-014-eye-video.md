# ICD-014 — Eye video

> **Status:** Skeleton · **Updated:** 2026-11-09 · **Requirements:** INF-006, EYE-019 · **Spec tree:** [N² chart](../requirements/spec-tree.md)

Video from each eye Pi to its projector.

```yaml
id: ICD-014
title: Eye video
status: skeleton
ends:
  - {component: eye-pi-left}
  - {component: eye-pi-right}
  - {component: eye-projector}
medium: HDMI
```

## To be filled in
- **Connector:** the Pi 5's micro-HDMI to the projector's HDMI input.
- **Resolution and rate:** the projector's native resolution at 60 Hz (SYS-024; projector
  model TBD-012).
- **Mirroring:** done in the renderer *or* the projector's rear mode, not both (site
  config `mirror`, ICD-015).
- **Start-up:** the projector shows the input when powered, without a remote (EYE-019).
