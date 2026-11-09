# ICD-002 — Radar targets

> **Status:** Draft · **Updated:** 2026-11-09 · **Requirements:** EAR-006, SHW-025, SIM-002 · **Spec tree:** [N² chart](../requirements/spec-tree.md)

The radar (an HLK-LD2450 read by an ESP32 running ESPHome) reports up to three people's
positions and speeds, a target count, and its own online/offline status. The fake radar
sends exactly the same messages (SIM-002). Facts about ESPHome below are from its
[LD2450](https://esphome.io/components/sensor/ld2450/) and
[MQTT](https://esphome.io/components/mqtt/) pages, checked 2026-11-09.

```yaml
id: ICD-002
title: Radar targets
status: draft
ends:
  - {component: radar-firmware}
  - {component: monster-brain}
  - {component: fake-radar}
medium: MQTT through mosquitto, over Wi-Fi (2.4 GHz); ESPHome's own topic layout
messages:
  - name: target value
    topic: monster-radar/sensor/target_{n}_{field}/state
    from: [radar-firmware, fake-radar]
    to: monster-brain
    qos: 0
    retain: true
    rate: about 10 per second per value while someone is in range (EAR-004)
    payload_format: plain-text number (exact number format to confirm, TBD-030)
    payload_schema: {type: string}
    examples: ["-312", "1840", "0"]
  - name: target count
    topic: monster-radar/sensor/target_count/state
    from: [radar-firmware, fake-radar]
    to: monster-brain
    qos: 0
    retain: true
    rate: about 10 per second while someone is in range
    payload_format: plain-text whole number, 0 to 3
    payload_schema: {type: string, enum: ["0", "1", "2", "3"]}
    examples: ["2"]
  - name: status
    topic: monster-radar/status
    from: [radar-firmware, fake-radar]
    to: monster-brain
    qos: 0
    retain: true
    rate: on connect (online); the broker sends the last-will (offline) if the node drops
    payload_schema: {enum: [online, offline]}
    examples: [online, offline]
```

## Values

`{n}` is the target slot, 1 to 3. `{field}` is one of:

| Field | Unit | Range and sign | Source |
|---|---|---|---|
| `x` | mm | -3000 to 3000; negative is left of the sensor, positive right | ESPHome LD2450 page |
| `y` | mm | 0 (closest) to 6000 (furthest), away from the sensor | ESPHome LD2450 page |
| `speed` | mm/s | Sign convention not documented (TBD-030) | ESPHome LD2450 page |

The topic names follow ESPHome's pattern `<node name>/sensor/<sensor id>/state`; our
ESPHome configuration (`esphome/`, Stage 2) must name its sensors so the ids come out as
`target_1_x` … `target_3_speed` and `target_count`. These names are the ones in
`shared/topics.py`.

**Positions are radar-relative.** The brain converts them to house coordinates using the
radar's mount position in the site config (SHW-006, [ICD-015](ICD-015-site-config.md)).
The brain also decides whether a visitor is in the approach zone or the door zone, from
`x` and `y`, so no zone topic is needed here (EAR-005).

## Not used yet

ESPHome also offers per-target `angle`, `distance` and `resolution`, still/moving counts,
three zone counts, presence binary sensors, and a per-target `direction` text sensor
(`Approaching`, `Moving away`, `Stationary`). The `direction` sensor could tell coming
from going (SYS-049), but it would add a topic that `shared/topics.py` doesn't have.
That is the owner's call under TBD-030.

## Timing

- ESPHome throttles each LD2450 sensor to one value per second by default
  (`throttle_with_priority: 1000ms`). Our configuration must override it to reach about
  10 per second (EAR-004, SYS-028).
- `x`, `y` and `speed` for one target arrive as three separate messages. The brain treats
  a target as updated when `x` or `y` changes.
- This hop's share of SYS-019's end-to-end time is in
  [timing-budgets.md](../requirements/timing-budgets.md) (TBD-034).

## Failure behavior

- **Radar node drops:** the broker publishes the `offline` last-will; the brain goes to
  ambient mode (SHW-018).
- **No values for TBD-023 while `online`:** the brain treats the radar as silent and goes
  to ambient mode too.
- **A person vanishes:** ESPHome stops reporting that slot. Near the door this is
  expected (SHW-011 door hold); elsewhere it ends the visitor.
