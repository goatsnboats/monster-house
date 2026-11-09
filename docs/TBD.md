# TBD register

> **Status:** Current · **Updated:** 2026-11-08 · Every open question in the project, with what will settle it.

TBDs are allowed in any document, but each one gets an ID here so none is lost.

- **In a document,** write `TBD-NNN` next to the unknown value or text, e.g.
  `window_m: {w: 0.0, h: 0.0}  # TBD-006`. Never write a bare "TBD".
- **To add one,** take the next number and fill in every column. If a trade study or an
  owner decision will settle it, link to it.
- **When one is resolved,** set its status to `Closed` with the date and a link to what
  closed it (an ADR, a measurement, a commit), and update the documents that cite it.
  Closed rows stay, as history.

**Resolved by:**
- `Trade study`: a study in [trades/](trades/), which ends in an ADR
- `Owner decision`: a matter of taste or priority
- `Measurement`: something to measure at the house
- `Test`: a hands-on test with real hardware
- `Verify`: check a fact against documentation or a vendor

## Open

| ID | What is undecided | Resolved by | Blocks | Needed by | Status |
|---|---|---|---|---|---|
| TBD-003 | How our MQTT message schemas are defined and validated (dataclasses, pydantic, msgspec, JSON Schema) | Trade study (not started). TBD-002 is closed (Python renderer, [ADR 0002](decisions/0002-eye-renderer.md)), so every component is Python; still depends on the ICD format from [ADR 0001](decisions/0001-requirements-and-architecture-format.md) | The `shared/` schemas; Stage 0 Step 1 "done when" | Stage 0 Step 1 | Open |
| TBD-004 | Lopsided eyes (one big, one small) or matched eyes | Owner decision, using the house preview | Eye art, per-eye config | Stage 0 exit | Open |
| TBD-005 | Each projector on its side (tall eye) or flat | Owner decision, after TBD-006 and TBD-017 | Per-eye `rotate_deg`, stands | Stage 0 exit | Open |
| TBD-006 | Glass width × height of both windows, fixed dividers, floor space behind each | Measurement | Screen size, projector distance, TBD-005 | Stage 0 exit | Open |
| TBD-007 | Porch roofline and railing length | Measurement | LED quantity, power supply | Stage 4 purchase | Open |
| TBD-008 | Wi-Fi signal strength on the porch (2.4 GHz) | Measurement | Radar and lip-controller placement | Stage 2 | Open |
| TBD-009 | Window grids: embrace them, or remove them for the season | Test in the real window | Eye art, screen mounting | Stage 1 | Open |
| TBD-010 | Where the show brain sits inside the front door, and the cable route to the amp | Owner decision | Stage 3 install | Stage 3 | Open |
| TBD-011 | The monster's name, and who voices it | Owner decision | Voice lines, theme content | Stage 0 Step 7 | Open |
| TBD-012 | Projector model (AAXA P400 class, or the budget fallback) | Trade study (not started) | Stage 1 purchase, Stage 1 cost | Stage 0 exit | Open |
| TBD-013 | Whether to buy a Pi 5 (1GB) early, for real renderer measurements | Owner decision. [TS-002](trades/TS-002-eye-renderer.md) recommends it: ADR 0002's main open risk is that moderngl at OpenGL 3.1 / ES 3.1 and SDL's KMS/DRM output are untested on a real Pi 5 | Confirming [ADR 0002](decisions/0002-eye-renderer.md) on hardware before Step 2 builds on it | Before or during Stage 0 Step 2 | Open |
| TBD-014 | Stage 1 cost: the uploaded and starter-kit versions of `architecture.md` disagree ($500–650 for two pods vs ~$415–515 per pod) | Owner decision, folded into TBD-012 | Stage 1 budget | Stage 0 exit | Open |
| TBD-015 | FPP's exact MQTT topics and HTTP API for the version we install | Verify against the installed FPP | ICD brain ↔ FPP; fake-FPP parity | Stage 3 (fake FPP in Stage 0 uses best-known topics) | Open |
| TBD-016 | Whether the radar's ~6 m range reaches the sidewalk | Measurement | Approach zone, greeting timing | Stage 2 | Open |
| TBD-017 | Whether the projector may run on its side (venting, manufacturer approval) | Verify with the manufacturer | TBD-005 | Stage 0 exit | Open |
| TBD-018 | Mount positions of the radar and both windows in house coordinates | Measurement at install | Gaze math settings | Stage 2 | Open |
| TBD-019 | When to move the architecture (not the requirements) to SysML v2 text notation, i.e. TS-001 option D | New trade study, once a command-line SysML v2 validator runs on Ubuntu and its views are readable. Check tool status at each stage boundary | Nothing yet; [ADR 0001](decisions/0001-requirements-and-architecture-format.md) keeps the content SysML-ready | Not before Stage 1 | Deferred |

## Closed

| ID | What was undecided | Closed by | Date |
|---|---|---|---|
| TBD-001 | How requirements, architecture and ICDs are documented | [ADR 0001](decisions/0001-requirements-and-architecture-format.md): Markdown + YAML with our own checker, SysML-ready (owner; [TS-001](trades/TS-001-requirements-approach.md)) | 2026-11-08 |
| TBD-002 | Eye renderer: Python + moderngl + pygame-ce, or Godot | [ADR 0002](decisions/0002-eye-renderer.md): Python + moderngl + pygame-ce (owner; [TS-002](trades/TS-002-eye-renderer.md), [results](trades/results/TS-002/README.md)) | 2026-11-08 |
