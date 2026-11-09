# ICD-001 — Eye commands and eye status

> **Status:** Draft · **Updated:** 2026-11-09 · **Requirements:** SHW-024, EYE-015, SIM-006 · **Spec tree:** [N² chart](../requirements/spec-tree.md)

The brain tells both eyes where to look, which expression to show, when to blink and
which theme's art to load. Each eye works out its own angle from its own window position
(EYE-003), so the brain sends one point, not two angles. Each eye reports online/offline
using MQTT's last-will. The house preview listens like a third eye.

```yaml
id: ICD-001
title: Eye commands and eye status
status: draft
ends:
  - {component: monster-brain}
  - {component: eye-renderer}
  - {component: house-preview}
medium: MQTT through mosquitto, over Wi-Fi (desktop loopback in Stage 0)
messages:
  - name: look
    topic: monster/eyes/look
    from: monster-brain
    to: [eye-renderer, house-preview]
    qos: 0
    retain: false
    rate: about 10 per second while a visitor is tracked (SHW-009); on change otherwise
    payload_schema:
      oneOf:
        - type: object
          required: [x, y, z]
          additionalProperties: false
          properties: {x: {type: number}, y: {type: number}, z: {type: number}}
        - type: object
          required: [mode]
          additionalProperties: false
          properties: {mode: {enum: [idle]}}
    examples:
      - {x: 1.2, y: 3.5, z: 1.0}
      - {mode: idle}
  - name: expression
    topic: monster/eyes/expression
    from: monster-brain
    to: [eye-renderer, house-preview]
    qos: 1
    retain: false
    rate: on change
    payload_schema:
      type: object
      required: [name, ms]
      additionalProperties: false
      properties:
        name: {enum: [neutral, happy, sparkle, surprised, sleepy, asleep]}
        ms: {type: integer, minimum: 0}
    examples:
      - {name: happy, ms: 300}
  - name: blink
    topic: monster/eyes/blink
    from: monster-brain
    to: [eye-renderer, house-preview]
    qos: 0
    retain: false
    rate: at the theme's blink interval while awake (SHW-015)
    payload_schema:
      type: object
      required: [ms]
      additionalProperties: false
      properties: {ms: {type: integer, minimum: 0}}
    examples:
      - {ms: 180}
  - name: theme
    topic: monster/theme
    from: monster-brain
    to: [eye-renderer, house-preview]
    qos: 1
    retain: true
    rate: on change
    payload_schema:
      type: object
      required: [name]
      additionalProperties: false
      properties: {name: {type: string}}
    examples:
      - {name: halloween}
  - name: status
    topic: monster/eyes/{side}/status
    from: eye-renderer
    to: monster-brain
    qos: 1
    retain: true
    rate: on connect (online); the broker sends the last-will (offline) if the eye drops
    payload_schema: {enum: [online, offline]}
    examples: [online, offline]
```

## Messages in words

| Message | Meaning |
|---|---|
| `look` with `x, y, z` | Look at this point: meters, in house coordinates (defined in [ICD-015](ICD-015-site-config.md)) |
| `look` with `mode: idle` | Wander and look around on your own (EYE-007) |
| `expression` | Ease into the named expression over `ms` milliseconds (values: architecture §2 table) |
| `blink` | Blink now, taking `ms` milliseconds. One message makes both eyes blink together |
| `theme` | Load this theme's eye art and colors (retained, so a restarted eye gets it at once) |
| `monster/eyes/{side}/status` | `{side}` is `left` or `right` (from the street). `online` when connected; `offline` as the last-will |

**Encoding:** commands are JSON objects in UTF-8; the status is plain text. How the code
defines and validates these payloads is still open (TBD-003); the wire format above
follows architecture §2.

## Timing

- **Look rate:** about 10 per second while tracking (SYS-028). A look point is therefore
  up to about 0.1 s old when sent.
- **Eye reaction:** the eye starts moving within its share of SYS-019 (TBD-020, split in
  TBD-034; see [timing-budgets.md](../requirements/timing-budgets.md)).
- **Blinks:** both eyes act on the same message, so they blink together within one frame
  plus network jitter.

## Failure behavior

- **Malformed message:** the eye ignores it and keeps its last target (EYE-015).
- **Brain silent for TBD-023:** each eye wanders and blinks on its own fallback timer
  until messages return (EYE-006).
- **An eye drops off:** the broker publishes its `offline` last-will; the brain logs it and
  carries on (SHW-018).

## QoS choices

Look points and blinks use QoS 0: a lost look point is replaced 0.1 s later, and a late
blink is worse than a missed one. Expressions, theme and status use QoS 1 because a lost
one would leave an eye wrong until the next change.
