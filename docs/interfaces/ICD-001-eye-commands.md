# ICD-001 — Eye commands and eye status

> **Status:** Stub · **Plan:** Written in full at STOP 2. · **Spec tree:** [spec-tree.md](../requirements/spec-tree.md)

The brain tells both eyes where to look, which expression to show, when to blink and which theme's art to load. Each eye reports online/offline with MQTT's last-will. The house preview (SIM) listens like a third eye.

```yaml
id: ICD-001
title: Eye commands and eye status
status: stub
ends:
  - {component: monster-brain}
  - {component: eye-renderer}
medium: MQTT through mosquitto, over Wi-Fi
```
