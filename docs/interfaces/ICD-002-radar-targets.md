# ICD-002 — Radar targets

> **Status:** Draft · **Updated:** 2026-11-23 · **Requirements:** EAR-006, SHW-025, SIM-002 · **Spec tree:** [N² chart](../requirements/spec-tree.md)

The radar (an HLK-LD2450 read by an ESP32 running ESPHome) reports up to three people's
positions and speeds, a target count, and its own online/offline status. The fake radar
sends exactly the same messages (SIM-002). Facts about ESPHome below are from its
[LD2450](https://esphome.io/components/sensor/ld2450/) and
[MQTT](https://esphome.io/components/mqtt/) pages, checked 2026-11-09, and from its
source code (`esphome/components/ld2450/`, `sensor/`, `mqtt/` on the `dev` branch), read
2026-11-23. Check them again against the ESPHome version we install (Stage 2).

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
    rate: when the value changes, at most about 10 per second per value (EAR-004)
    payload_format: plain-text whole number (no decimals), or nan when the slot is empty
    payload_schema: {type: string}
    examples: ["-312", "1840", "-250", "0", "nan"]
  - name: target count
    topic: monster-radar/sensor/target_count/state
    from: [radar-firmware, fake-radar]
    to: monster-brain
    qos: 0
    retain: true
    rate: when the count changes, at most about 10 per second
    payload_format: plain-text whole number, 0 to 3, or nan while the ESP32 can't hear the radar module
    payload_schema: {type: string, enum: ["0", "1", "2", "3", "nan"]}
    examples: ["2", "0", "nan"]
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
| `x` | mm | -3000 to 3000; negative is left of the sensor, positive right. Which side is "left" as seen from the street is checked at install (TBD-039) | ESPHome LD2450 page |
| `y` | mm | 0 (closest) to 6000 (furthest), away from the sensor | ESPHome LD2450 page |
| `speed` | mm/s | Negative: moving toward the radar. Positive: moving away from it. 0: standing still. Steps of 10 (the module reports cm/s) | ESPHome source (`decode_speed`; its `direction` sensor says `Approaching` for negative) |

**Number format.** Each value is a whole number with no decimals and no unit, e.g. `-312`
(ESPHome's default for these sensors is `accuracy_decimals: 0`). When a slot has no one
in it, ESPHome publishes "unknown", which reaches MQTT as the text `nan` for `x`, `y`
and `speed`. When the ESP32 loses touch with the radar module itself, every value,
including `target_count`, becomes `nan` until it hears from the module again. Our
ESPHome configuration must not set the MQTT option that turns `nan` into `None`.

The topic names follow ESPHome's pattern `<node name>/sensor/<sensor id>/state`; our
ESPHome configuration (`esphome/`, Stage 2) must name its sensors so the ids come out as
`target_1_x` … `target_3_speed` and `target_count`. These names are the ones in
`shared/topics.py`.

**Positions are radar-relative.** The brain converts them to house coordinates using the
radar's mount position in the site config (SHW-006, [ICD-015](ICD-015-site-config.md)).
The brain also decides whether a visitor is in the approach zone or the door zone, from
`x` and `y`, so no zone topic is needed here (EAR-005).

**Coming or going** (SYS-049, SHW-010) is worked out by the brain from how a visitor's
position changes over about half a second, in house coordinates (owner, 2026-11-23,
closing TBD-030). So "coming" means toward the house even if the radar ends up at an
angle (TBD-037). The `speed` value is still sent, with ESPHome's sign, but the brain
doesn't need it.

## Not used yet

ESPHome also offers per-target `angle`, `distance` and `resolution`, still/moving counts,
three zone counts, presence binary sensors, and a per-target `direction` text sensor
(`Approaching`, `Moving away`, `Stationary`, `NA`). The `direction` sensor is only the
sign of `speed` put into words, measured toward the radar rather than the house; the
owner chose not to use it (TBD-030, closed 2026-11-23).

## Timing

- **Only changes are sent.** ESPHome publishes a value only when it differs from the
  last one it published. Someone standing perfectly still sends nothing new, and an
  empty walk sends nothing at all. So **silence is normal** and never means the radar
  has failed.
- **Throttle.** By default each LD2450 sensor has a `timeout` filter and a
  `throttle_with_priority` filter, both 1000 ms: at most one value a second, a `nan`
  goes through at once, and the last value is sent once more a second after the
  changes stop. Our configuration must set both to 100 ms to reach about 10 per second
  (EAR-004, SYS-028). The fake radar behaves like that configuration.
- `x`, `y` and `speed` for one target arrive as three separate messages. The brain treats
  a target as updated when `x` or `y` changes, and as gone when `x` or `y` is `nan`.
- This hop's share of SYS-019's end-to-end time is in
  [timing-budgets.md](../requirements/timing-budgets.md) (TBD-034).

## Failure behavior

- **Radar node drops:** the broker publishes the `offline` last-will; the brain goes to
  ambient mode (SHW-018).
- **The ESP32 loses the radar module** (a loose wire): every value becomes `nan` while the
  node stays `online`. The brain sees nobody, and the monster stays asleep or says
  goodbye. Telling this apart from an empty walk would need ESPHome's `connected`
  sensor, which isn't in this ICD.
- **No values while `online`:** normal, nobody is moving (see Timing). Silence alone
  never sends the brain to ambient mode.
- **A person vanishes:** ESPHome sends `nan` for that slot's `x`, `y` and `speed`. Near
  the door this is expected (SHW-011 door hold); elsewhere it ends the visitor.
