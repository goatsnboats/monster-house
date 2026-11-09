# ICD-008 — Power

> **Status:** Skeleton · **Updated:** 2026-11-09 · **Requirements:** INF-011, EYE-020, EAR-009, MTH-007, VOC-005 · **Spec tree:** [N² chart](../requirements/spec-tree.md)

How each box gets mains power: one plug per box (SYS-034).

```yaml
id: ICD-008
title: Power
status: skeleton
ends:
  - {component: power-distribution}
  - {component: eye-power-strip}
  - {component: radar-psu}
  - {component: lip-psu}
  - {component: amp-psu}
  - {component: porch-pi}
medium: Mains, then each box's own supply
```

## To be filled in
| Box | Where | Plug |
|---|---|---|
| Each eye pod (power strip: Pi + projector) | Bedroom, by each window | Bedroom outlet |
| Porch Pi | Inside the front door (TBD-010) | Indoor outlet |
| Radar 5 V supply | Porch | Outdoor-rated outlet or cord |
| Lip 12 V supply (~350 W) | Porch, lip box | Outdoor-rated outlet or cord |
| Amp 24 V supply | Porch box or inside the door (TBD-010) | Outdoor or indoor outlet |

- **Loads:** added to the budget check as they become known (lip draw: TBD-033).
- **Bedtime:** whether the eye pods' power is switched at bedtime is TBD-025 (INF-012).
