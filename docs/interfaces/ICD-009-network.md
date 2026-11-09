# ICD-009 — Network service

> **Status:** Stub · **Plan:** A skeleton with TBDs at STOP 2. · **Spec tree:** [spec-tree.md](../requirements/spec-tree.md)

What the home network gives every networked node: Wi-Fi coverage, a reserved address and friendly name, clock sync, and no exposure to the internet.

```yaml
id: ICD-009
title: Network service
status: stub
ends:
  - {component: home-network}
  - {component: eye-pi-left}
  - {component: eye-pi-right}
  - {component: porch-pi}
  - {component: radar-esp32}
  - {component: lip-controller}
medium: Wi-Fi, reserved addresses, names, clock sync
```
