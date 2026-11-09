# ICD-003 — Clip commands and clip status

> **Status:** Draft (best-known FPP topics, to verify: TBD-015) · **Updated:** 2026-11-09 · **Requirements:** SHW-026, SHW-035, SIM-004 · **Spec tree:** [N² chart](../requirements/spec-tree.md)

The brain starts a voice-and-lips clip by name, and Falcon Player says when it is
playing and when it has finished. Each clip is a one-item FPP playlist with the same name
as its audio file and lip sequence (THM-006). The link is inside Show control, but has
its own ICD so the fake FPP (Stages 0–2) can be swapped for the real one (SYS-043).

The topics are the best known from architecture §3a. FPP's exact MQTT topics and
payloads must be checked against the FPP version we install (TBD-015); the fake FPP and
this ICD change together if they differ. FPP's HTTP API is the fallback if its MQTT
control doesn't suit.

```yaml
id: ICD-003
title: Clip commands and clip status
status: draft
ends:
  - {component: monster-brain}
  - {component: falcon-player}
  - {component: fake-fpp}
medium: MQTT through mosquitto (FPP's HTTP API as fallback, TBD-015)
messages:
  - name: start clip
    topic: falcon/player/FPP/set/playlist/{name}/start
    from: monster-brain
    to: [falcon-player, fake-fpp]
    qos: 1
    retain: false
    rate: at most one per clip; the brain keeps the theme's minimum gap (SHW-017)
    payload_format: empty
  - name: player status
    topic: falcon/player/FPP/status
    from: [falcon-player, fake-fpp]
    to: monster-brain
    qos: 0
    retain: true
    rate: on change (best known, TBD-015)
    payload_schema: {enum: [playing, idle]}
    examples: [playing, idle]
  - name: playlist playing
    topic: falcon/player/FPP/playlist/name/status
    from: [falcon-player, fake-fpp]
    to: monster-brain
    qos: 0
    retain: true
    rate: on change (best known, TBD-015)
    payload_format: plain text, the playlist (clip) name
    payload_schema: {type: string}
    examples: [greet_01]
```

## How a clip plays

1. The brain publishes `start clip` with `{name}` set to the clip, e.g. `greet_01`.
2. FPP plays the audio and the lip sequence together (SHW-032), publishes `playing` and
   the playlist name.
3. When the clip ends, FPP publishes `idle`. The brain treats that as "clip finished"
   (for example to move from Waking to Greeting).

`FPP` in the topics is the player's host name in FPP's settings (`shared/topics.py`).

## The fake FPP

It subscribes to the same command topic, logs each trigger, plays
`themes/<theme>/audio/<name>.wav` through the desktop speakers, and publishes the same
status messages: `playing` at the start and `idle` when the audio ends.

## Timing

- FPP starts a clip within its share of SYS-021 (TBD-022, split in TBD-034).
- Lips vs voice: FPP plays both from one playlist, which is how SYS-022 is met.

## Failure behavior

- **No `playing` within TBD-023 of a start command, or FPP offline:** the brain treats FPP
  as not responding, keeps the eyes going, and stops waiting for clips (SHW-018).
- **Muted:** the brain sends no start commands (SHW-020).
