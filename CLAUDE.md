# Monster House

A friendly animated "monster face" on a house for Halloween 2027 (and other holidays). The two upstairs bedroom windows are **eyes** (rear-projected, drawn live so they can follow visitors). The porch is the **mouth** (LED lips). A radar sensor notices trick-or-treaters. A "monster brain" decides the monster's mood and tells everything else what to do.

Read these before making design decisions:
- `docs/architecture.md`: full system design, message topics, hardware, stages.
- `docs/stage-0-plan.md`: what we're building right now, step by step, with "done when" criteria.
- `docs/reference/eye-sketch.html`: interactive sketch of the eye. Open it in a browser. It defines the look and the expression parameters to match.
- `docs/reference/house-front.jpg`: photo of the house, for the house preview.
- `docs/TBD.md`: every open question, with what will resolve it. A TBD in any file must cite its `TBD-NNN` ID; never write a bare "TBD".
- `docs/requirements/`: the requirements baseline (spec tree, `SYS-` and subsystem *shall* requirements, generated `trace.md`), with `docs/architecture/components.yaml` and the ICDs in `docs/interfaces/`. Trace design decisions to requirement IDs, and run `.venv/bin/python -m tools.reqs.check` after changing any of them.
- `docs/trades/` and `docs/decisions/`: trade studies and the decisions (ADRs) they produce. Run the `trade-study` skill for choices in the **design of the system** (what goes on the house and the software it runs: hardware, libraries, approaches) with two or more defensible options. For **general infrastructure** (docs site, checker, dev tooling, CI, workflow), consider the alternatives briefly and recommend one; no formal study (owner, 2026-11-11).

## Current stage: Stage 0 (software-only prototype on the desktop)
No hardware yet. Everything runs on one desktop: Mosquitto, the monster brain, both eyes (as windows), a fake radar, and a fake Falcon Player. Later stages move the eyes to Raspberry Pi 5 (1GB) pods and the brain to a porch Pi, so **everything must stay portable to Raspberry Pi OS (64-bit, Debian-based)**.

## Tone
Friendly, goofy, delighted to see visitors. Never scary. Big round pupils, smiles made with the lower lid, no slit pupils, no horror sounds.

## Architecture rules
- **One brain, simple limbs.** All decisions live in `brain/`. Eye renderers, radar and lights only report or obey.
- **Everything talks over MQTT** (Mosquitto). Topic names and payload formats live in one place (`shared/`) and nowhere else. Don't hard-code topic strings in components.
- **Simulator parity.** Every hardware piece has a simulator that sends or receives *exactly* the same messages as the real thing (fake radar mimics ESPHome's LD2450 topics; fake FPP mimics Falcon Player's MQTT/HTTP interface closely enough to swap later).
- **Fail friendly.** If a component disappears, the rest keeps working and the monster just looks sleepy. Never show an error on the eye screens.
- **Themes are data.** Timings, clip pools, colors and eye art come from `themes/<name>/`, not code.
- **Configuration in YAML files**, including per-eye window settings (size, position, rotation, mirroring, brightness). The two windows are different sizes.

## Eye renderer constraints
- Drawn on the **GPU**. Shaders must be compatible with **OpenGL ES 3.0 / GLSL ES 3.00** (the Pi 5 target). Don't draw on the CPU per frame.
- **60 fps** target. Must run in a desktop window (development) and full-screen without a desktop environment on the Pi (KMS/DRM) later.
- Supports: rotation 0/90°, horizontal mirroring (rear projection), and per-eye placement within its window.
- Expression = numbers (`open`, `low`, `curve`, `pupil`, `spark`, iris color) that ease smoothly; see the table in `docs/architecture.md` §2.
- Pupils glide toward targets with smoothing plus tiny micro-movements; blinks are commanded by the brain (with a fallback timer if the brain goes quiet).

## Coding conventions
- Python 3.11+, type hints, small modules. Use a virtual environment; pin dependencies.
- Tests with `pytest` for anything with logic: mood transitions, gaze math, clip-pool shuffling, config loading. Run tests before finishing any task.
- Prefer plain, readable code over clever code. The owner reads it but isn't a full-time developer.
- Keep a short `README.md` per component with "how to run it."
- Ask before adding a heavy dependency or changing a message format.

## Working style for this repo
- Start each task by restating the goal and the "done when" from `docs/stage-0-plan.md`, then propose a short plan.
- Stop and ask when a decision is a matter of taste (look, timing, personality) or would change the architecture. Make the reasonable call on purely technical details and mention it.
- When a task is done: run the tests, show how to run/see the result, and update the relevant README and the plan checklist.

## Glossary
- **Eye pod:** Pi + projector + screen at one window (Stage 1+). In Stage 0, an eye window on the desktop.
- **Brain:** The mood state machine + gaze math + clip triggers (`brain/`).
- **FPP:** Falcon Player, which plays voice clips with matching lip-light sequences (Stage 3+). Faked in Stage 0.
- **LD2450:** The radar. Reports X/Y (mm) for up to 3 people, via ESPHome over MQTT.
- **Moods:** Asleep → Waking → Greeting → Watching → Goodbye (→ Asleep, or back to Greeting).
