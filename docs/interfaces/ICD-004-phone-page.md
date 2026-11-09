# ICD-004 — Phone buttons and current mood

> **Status:** Draft (proposed format, owner to confirm) · **Updated:** 2026-11-09 · **Requirements:** SHW-030, SHW-031 · **Spec tree:** [N² chart](../requirements/spec-tree.md)

The owner's phone opens a small web page served by the brain on the home network. The
page shows the current mood and sends button presses and a theme choice. Nothing here
existed before this ICD; the HTTP paths and the `monster/state` payload are **proposals**
for the owner to confirm. The topic name `monster/state` is from architecture §3b.

```yaml
id: ICD-004
title: Phone buttons and current mood
status: draft
ends:
  - {external: owner-phone}
  - {component: phone-page}
  - {component: monster-brain}
medium: HTTP on the home network (port 8080 on monster-brain); MQTT for the mood
messages:
  - name: page
    path: GET /
    from: owner-phone
    to: phone-page
    payload_format: an HTML page that works in an ordinary phone browser, no app
  - name: state
    path: GET /api/state
    from: owner-phone
    to: phone-page
    rate: when the page opens, then every few seconds while it is open
    payload_schema:
      type: object
      required: [mood, muted, theme, themes]
      additionalProperties: false
      properties:
        mood: {enum: [asleep, waking, greeting, watching, goodbye]}
        muted: {type: boolean}
        theme: {type: string}
        themes: {type: array, items: {type: string}}
    examples:
      - {mood: watching, muted: false, theme: halloween, themes: [halloween]}
  - name: button
    path: POST /api/button
    from: owner-phone
    to: phone-page
    rate: when pressed
    payload_schema:
      type: object
      required: [name]
      additionalProperties: false
      properties:
        name: {enum: [costume, burp, sing, mute, unmute, sleep, wake]}
    examples:
      - {name: costume}
  - name: choose theme
    path: POST /api/theme
    from: owner-phone
    to: phone-page
    rate: when chosen
    payload_schema:
      type: object
      required: [name]
      additionalProperties: false
      properties: {name: {type: string}}
    examples:
      - {name: halloween}
  - name: mood
    topic: monster/state
    from: monster-brain
    to: phone-page
    qos: 1
    retain: true
    rate: on change (SHW-022)
    payload_schema:
      type: object
      required: [mood]
      additionalProperties: false
      properties:
        mood: {enum: [asleep, waking, greeting, watching, goodbye]}
    examples:
      - {mood: asleep}
```

## Buttons

| `name` | Does |
|---|---|
| `costume` | Great costume: sparkle eyes and a compliment |
| `burp`, `sing` | Play a clip from that pool |
| `mute`, `unmute` | No voice while muted; eyes and lights carry on (SYS-013) |
| `sleep`, `wake` | Go to sleep now / wake up now |

Answers: `204 No Content` when accepted; `400` with a short message for an unknown
button or theme.

## Timing

A button must visibly change the monster within 0.5 s (SYS-023). The brain's share is in
[timing-budgets.md](../requirements/timing-budgets.md) (TBD-034).

## Failure behavior

If the brain is down, the phone simply can't load the page; nothing shows on the eyes.
The page answers only on the home network (SYS-038).
