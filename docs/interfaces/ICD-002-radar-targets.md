# ICD-002 — Radar targets

> **Status:** Stub · **Plan:** Written in full at STOP 2. · **Spec tree:** [spec-tree.md](../requirements/spec-tree.md)

The radar reports up to three people's positions and speeds, a target count and its online/offline status. The fake radar (SIM) sends exactly the same messages.

```yaml
id: ICD-002
title: Radar targets
status: stub
ends:
  - {component: radar-firmware}
  - {component: monster-brain}
medium: MQTT through mosquitto (ESPHome LD2450 topics), over Wi-Fi
```
