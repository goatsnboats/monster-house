# ICD-015 — Site config

> **Status:** Draft (new file, owner to confirm) · **Updated:** 2026-11-09 · **Requirements:** INF-007, SHW-028, EYE-017 · **Spec tree:** [N² chart](../requirements/spec-tree.md)

The house's own settings, the same for every theme (spec tree Q6): where the eyes and the
radar are, each eye's window settings, the zones, and the door. It replaces the positions
in architecture §3b's theme settings and the per-eye block in architecture §2. The
numbers in the example are the architecture's placeholders; the real ones are measured at
install (TBD-006, TBD-018, TBD-029).

**House coordinates** (meters): the origin is the ground point directly below the radar;
`x` is to the right as seen from the street, `y` points from the house toward the street,
and `z` is up. The radar's own readings are millimeters relative to the radar
([ICD-002](ICD-002-radar-targets.md)).

```yaml
id: ICD-015
title: Site config
status: draft
ends:
  - {component: site-config}
  - {component: monster-brain}
  - {component: eye-renderer}
medium: File config/site.yaml (the repository on the desktop; copied to the Pis)
files:
  - name: site
    path: config/site.yaml
    from: site-config
    to: [monster-brain, eye-renderer]
    payload_schema:
      type: object
      required: [radar, head_height_m, eyes]
      additionalProperties: false
      properties:
        radar:
          type: object
          required: [mount, approach_range_m]
          additionalProperties: false
          properties:
            mount:
              type: object
              required: [x, y, z]
              properties: {x: {type: number}, y: {type: number}, z: {type: number}}
            approach_range_m: {type: number, minimum: 0}
            door_zone_mm:
              type: object
              required: [x1, y1, x2, y2]
              properties: {x1: {type: number}, y1: {type: number}, x2: {type: number}, y2: {type: number}}
        door_point:
          type: object
          required: [x, y, z]
          properties: {x: {type: number}, y: {type: number}, z: {type: number}}
        head_height_m: {type: number, minimum: 0}
        eyes:
          type: object
          required: [left, right]
          additionalProperties: false
          properties:
            left: &eye
              type: object
              required: [position_m, window_m, rotate_deg, mirror, eye_center, eye_size, brightness]
              additionalProperties: false
              properties:
                position_m:
                  type: object
                  required: [x, y, z]
                  properties: {x: {type: number}, y: {type: number}, z: {type: number}}
                window_m:
                  type: object
                  required: [w, h]
                  properties: {w: {type: number, minimum: 0}, h: {type: number, minimum: 0}}
                rotate_deg: {enum: [0, 90]}
                mirror: {type: boolean}
                eye_center: {type: array, items: {type: number, minimum: 0, maximum: 1}}
                eye_size: {type: number, minimum: 0, maximum: 1}
                brightness: {type: number, minimum: 0, maximum: 1}
            right: *eye
    examples:
      - radar:
          mount: {x: 0.0, y: 0.0, z: 1.2}
          approach_range_m: 5.0
        head_height_m: 1.0
        eyes:
          left:
            position_m: {x: -1.6, y: -0.5, z: 5.0}
            window_m: {w: 0.0, h: 0.0}
            rotate_deg: 90
            mirror: true
            eye_center: [0.5, 0.5]
            eye_size: 0.9
            brightness: 1.0
          right:
            position_m: {x: 1.6, y: -0.5, z: 5.0}
            window_m: {w: 0.0, h: 0.0}
            rotate_deg: 0
            mirror: true
            eye_center: [0.5, 0.5]
            eye_size: 0.9
            brightness: 1.0
```

## Fields

| Field | Meaning | Real value |
|---|---|---|
| `radar.mount` | Where the radar is, in house coordinates | Measured at install (TBD-018) |
| `radar.approach_range_m` | A visitor closer than this, coming toward the house, starts Waking | Architecture §3b gives 5.0 |
| `radar.door_zone_mm` | Rectangle in radar coordinates where the radar loses visitors at the door (SHW-011) | Measured at install (TBD-029); optional until then |
| `door_point` | Where the eyes look while a visitor is at the door (SHW-012) | Measured at install; optional until then |
| `head_height_m` | Assumed head height of a visitor | Architecture §3b gives 1.0 (kids), adjustable |
| `eyes.<side>.position_m` | Window center in house coordinates | TBD-018 |
| `eyes.<side>.window_m` | Glass width and height | TBD-006 |
| `eyes.<side>.rotate_deg` | 0, or 90 with the projector on its side | TBD-005 |
| `eyes.<side>.mirror` | Mirror horizontally for rear projection (here *or* in the projector, not both) | Architecture §2 |
| `eyes.<side>.eye_center`, `eye_size` | Where the eye sits in the window (0–1) and how big | Owner, from the house preview (TBD-004) |
| `eyes.<side>.brightness` | Matches the two eyes (a bigger image looks dimmer) | Owner, at install |

`left` is the smaller window, as seen from the street.

## Timing and failure behavior

Read at start-up. If the file is missing or broken, the brain and eyes start with a
sleepy idle look and log the problem; they never show an error (SYS-037).
