# ICD-009 — Network service

> **Status:** Skeleton · **Updated:** 2026-11-09 · **Requirements:** INF-008, EAR-007, MTH-006 · **Spec tree:** [N² chart](../requirements/spec-tree.md)

What the home network gives every networked node (architecture §8).

```yaml
id: ICD-009
title: Network service
status: skeleton
ends:
  - {component: home-network}
  - {component: eye-pi-left}
  - {component: eye-pi-right}
  - {component: porch-pi}
  - {component: radar-esp32}
  - {component: lip-controller}
medium: Wi-Fi, reserved addresses, names, clock sync
```

## To be filled in
| Node | Name | Band |
|---|---|---|
| `porch-pi` (or the desktop in Stages 0–2) | `monster-brain` | 2.4 or 5 GHz |
| `eye-pi-left` | `eye-left` | 2.4 or 5 GHz |
| `eye-pi-right` | `eye-right` | 2.4 or 5 GHz |
| `lip-controller` | `monster-lips` | 2.4 GHz |
| `radar-esp32` | `monster-radar` | 2.4 GHz |

- Each name has a reserved address in the router.
- Clocks sync automatically (show hours, SHW-019).
- Nothing is forwarded from the internet (INF-010).
- Porch signal strength: TBD-008.
