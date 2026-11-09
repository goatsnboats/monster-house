# ICD-005 — Theme folder

> **Status:** Draft (new keys proposed, owner to confirm) · **Updated:** 2026-11-09 · **Requirements:** THM-001, SHW-027, EYE-016 · **Spec tree:** [N² chart](../requirements/spec-tree.md)

A theme is a folder that gives the same hardware a holiday personality (architecture §9).
The brain reads its timings, clip pools and show hours; the eyes read its art and colors;
Falcon Player gets its audio and sequences through xLights (ICD-012).

**Changes from architecture §3b's settings example** (owner to confirm):
- the eye and radar positions and the head height move to the site config
  ([ICD-015](ICD-015-site-config.md)), because they describe the house, not the holiday
  (spec tree Q6);
- new timing keys: `snore_every_s` (architecture says "about every 30 s"), `min_gap_s`
  (§3b, 10 s), `focus_hold_s` (§3b, 3–6 s), `blink_every_s` and `blink_ms` (from the
  eye sketch: 2.5–6 s and 200 ms), `door_hold_s` (TBD-028);
- new clip pools `snore`, `sing`, `door` and `arrival` (owner, 2026-11-09);
- an `eyes:` section for colors (the sketch's iris and sclera colors as the example).

```yaml
id: ICD-005
title: Theme folder
status: draft
ends:
  - {component: theme-format}
  - {component: monster-brain}
  - {component: eye-renderer}
medium: Files in themes/<name>/ (the repository on the desktop; copied to the Pis)
files:
  - name: settings
    path: themes/{name}/settings.yaml
    from: theme-format
    to: [monster-brain, eye-renderer]
    payload_schema:
      type: object
      required: [theme, show_hours, volume_cap, timing, clips, eyes]
      additionalProperties: false
      properties:
        theme: {type: string}
        show_hours: {type: array, items: {type: string}}
        volume_cap: {type: number, minimum: 0, maximum: 100}
        timing:
          type: object
          required: [goodbye_after_s, sleep_after_s, comment_every_s, min_gap_s, snore_every_s,
                     blink_every_s, blink_ms, focus_hold_s]
          additionalProperties: false
          properties:
            goodbye_after_s: {type: number, minimum: 0}
            sleep_after_s: {type: number, minimum: 0}
            comment_every_s: {type: array, items: {type: number, minimum: 0}}
            min_gap_s: {type: number, minimum: 0}
            snore_every_s: {type: number, minimum: 0}
            blink_every_s: {type: array, items: {type: number, minimum: 0}}
            blink_ms: {type: integer, minimum: 0}
            focus_hold_s: {type: array, items: {type: number, minimum: 0}}
            door_hold_s: {type: number, minimum: 0}
        clips:
          type: object
          required: [wake, greet, comment, bye, costume, burp, sing, snore, door, arrival]
          additionalProperties: false
          properties:
            wake: {type: array, items: {type: string}}
            greet: {type: array, items: {type: string}}
            comment: {type: array, items: {type: string}}
            bye: {type: array, items: {type: string}}
            costume: {type: array, items: {type: string}}
            burp: {type: array, items: {type: string}}
            sing: {type: array, items: {type: string}}
            snore: {type: array, items: {type: string}}
            door: {type: array, items: {type: string}}
            arrival: {type: array, items: {type: string}}
        eyes:
          type: object
          required: [iris_color, sclera_color]
          additionalProperties: false
          properties:
            iris_color: {type: string}
            sclera_color: {type: string}
    examples:
      - theme: halloween
        show_hours: ["17:30", "21:30"]
        volume_cap: 70
        timing:
          goodbye_after_s: 5
          sleep_after_s: 20
          comment_every_s: [10, 20]
          min_gap_s: 10
          snore_every_s: 30
          blink_every_s: [2.5, 6.0]
          blink_ms: 200
          focus_hold_s: [3, 6]
        clips:
          wake: [yawn_01]
          greet: [greet_01, greet_02, greet_03, greet_04, greet_05]
          comment: [comment_01, comment_02, comment_03, giggle_01]
          bye: [bye_01, bye_02]
          costume: [costume_01, costume_02]
          burp: [burp_01]
          sing: []
          snore: [snore]
          door: []
          arrival: []
        eyes: {iris_color: "#7a55e0", sclera_color: "#f6f2e6"}
  - name: audio
    path: themes/{name}/audio/{clip}.wav
    from: theme-format
    to: monster-brain
    payload_format: 48 kHz audio, normalized to the same loudness (THM-004)
  - name: sequences
    path: themes/{name}/sequences/{clip}.fseq
    from: theme-format
    to: monster-brain
    payload_format: xLights lip sequence; uploaded to FPP with its audio (ICD-012)
  - name: eye art
    path: themes/{name}/eyes/
    from: theme-format
    to: eye-renderer
    payload_format: PNG or SVG art; which files the renderer reads is set when it uses them (Stage 0 Step 2)
```

## Rules

- Every clip name in `clips:` has `audio/<clip>.wav` and, from Stage 4,
  `sequences/<clip>.fseq`, and the FPP playlist has the same name (THM-006).
- An empty pool means "nothing to say" for that trigger (for example `arrival: []`, eyes
  only).
- `show_hours` is local time, `["start", "end"]`. The example is architecture §3a's; the
  real hours are TBD-024.
- `door_hold_s` is optional until TBD-028 is decided.

## Timing and failure behavior

Settings are read when a theme loads (SHW-021, EYE-014). A missing or broken
`settings.yaml` must not stop the monster: the brain keeps the theme it had and logs the
problem; the eyes keep their art (SYS-017).
