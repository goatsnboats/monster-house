# TBD register

> **Status:** Current · **Updated:** 2026-11-09 · Every open question in the project, with what will settle it.

TBDs are allowed in any document, but each one gets an ID here so none is lost.

- **In a document,** write `TBD-NNN` next to the unknown value or text, e.g.
  `window_m: {w: 0.0, h: 0.0}  # TBD-006`. Never write a bare "TBD".
- **To add one,** take the next number and fill in every column.
- **Gate** is the review by which it must be closed (SRR, PDR or CDR-1 to CDR-5; see
  [reviews/](reviews/README.md)). It is the burndown plan: each review's package lists
  the TBDs due at it, and `tools/reqs/check.py --review <gate>` reports which are still open. If a trade study or an
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

| ID | What is undecided | Resolved by | Blocks | Needed by | Gate | Status |
|---|---|---|---|---|---|---|
| TBD-003 | How our MQTT message schemas are defined and validated (dataclasses, pydantic, msgspec, JSON Schema) | Trade study (not started). TBD-002 is closed (Python renderer, [ADR 0002](decisions/0002-eye-renderer.md)), so every component is Python; still depends on the ICD format from [ADR 0001](decisions/0001-requirements-and-architecture-format.md) | The `shared/` schemas; Stage 0 Step 1 "done when" | Stage 0 Step 1 | PDR | Open |
| TBD-004 | Lopsided eyes (one big, one small) or matched eyes | Owner decision, using the house preview | Eye art, per-eye config | Stage 0 exit | PDR | Open |
| TBD-005 | Each projector on its side (tall eye) or flat | Owner decision, after TBD-006 and TBD-017 | Per-eye `rotate_deg`, stands | Stage 0 exit | CDR-1 | Open |
| TBD-006 | Glass width × height of both windows, fixed dividers, floor space behind each | Measurement | Screen size, projector distance, TBD-005 | Stage 0 exit | CDR-1 | Open |
| TBD-007 | Porch roofline and railing length | Measurement | LED quantity, power supply | Stage 4 purchase | CDR-4 | Open |
| TBD-008 | Wi-Fi signal strength on the porch (2.4 GHz) | Measurement | Radar and lip-controller placement | Stage 2 | CDR-2 | Open |
| TBD-009 | Window grids: embrace them, or remove them for the season | Test in the real window | Eye art, screen mounting | Stage 1 | CDR-1 | Open |
| TBD-010 | Where the show brain sits inside the front door, and the cable route to the amp | Owner decision | Stage 3 install | Stage 3 | CDR-3 | Open |
| TBD-011 | The monster's name, and who voices it | Owner decision | Voice lines, theme content | Stage 0 Step 7 | CDR-3 | Open |
| TBD-012 | Projector model (AAXA P400 class, or the budget fallback) | Trade study (not started) | Stage 1 purchase, Stage 1 cost | Stage 0 exit | PDR | Open |
| TBD-013 | Whether to buy a Pi 5 (1GB) early, for real renderer measurements | Owner decision. [TS-002](trades/TS-002-eye-renderer.md) recommends it: ADR 0002's main open risk is that moderngl at OpenGL 3.1 / ES 3.1 and SDL's KMS/DRM output are untested on a real Pi 5 | Confirming [ADR 0002](decisions/0002-eye-renderer.md) on hardware before Step 2 builds on it | Before or during Stage 0 Step 2 | PDR | Open |
| TBD-014 | Stage 1 cost: the uploaded and starter-kit versions of `architecture.md` disagree ($500–650 for two pods vs ~$415–515 per pod) | Owner decision, folded into TBD-012 | Stage 1 budget | Stage 0 exit | CDR-1 | Open |
| TBD-015 | FPP's exact MQTT topics and HTTP API for the version we install | Verify against the installed FPP | ICD brain ↔ FPP; fake-FPP parity | Stage 3 (fake FPP in Stage 0 uses best-known topics) | CDR-3 | Open |
| TBD-016 | Whether the radar's ~6 m range reaches the sidewalk | Measurement | Approach zone, greeting timing | Stage 2 | CDR-2 | Open |
| TBD-017 | Whether the projector may run on its side (venting, manufacturer approval) | Verify with the manufacturer | TBD-005 | Stage 0 exit | CDR-1 | Open |
| TBD-018 | Mount positions of the radar and both windows in house coordinates | Measurement at install | Gaze math settings | Stage 2 | CDR-2 | Open |
| TBD-019 | When to move the architecture (not the requirements) to SysML v2 text notation, i.e. TS-001 option D | New trade study, once a command-line SysML v2 validator runs on Ubuntu and its views are readable. Check tool status at each stage boundary | Nothing yet; [ADR 0001](decisions/0001-requirements-and-architecture-format.md) keeps the content SysML-ready | Not before Stage 1 | — | Deferred |
| TBD-020 | Longest acceptable delay from a visitor moving to the eyes following (SYS-019) | Owner decision, trying values in the Stage 0 simulator | Per-hop timing budget: radar rate, brain smoothing, eye glide | Stage 0 Step 4 | PDR | Open |
| TBD-021 | Longest acceptable delay from a visitor entering the approach zone to the monster starting to wake (SYS-020) | Owner decision, in the Stage 0 simulator | Approach-zone size, brain wake logic | Stage 0 Step 4 | PDR | Open |
| TBD-022 | Longest acceptable delay from the brain deciding to speak to the voice starting (SYS-021) | Owner decision; then a Test with the real FPP | Fake FPP timing, FPP trigger method (with TBD-015) | Stage 3 (fake FPP uses a placeholder in Stage 0) | CDR-3 | Open |
| TBD-023 | How quickly each failure (eye pod, brain, radar, FPP) must be noticed and the fallback begin (SYS-029) | Owner decision | MQTT keep-alive and last-will settings, eye fallback timer | Stage 0 Step 2 (eye fallback timer) | PDR | Open |
| TBD-024 | Show hours (architecture §3a gives 5:30–9:30 pm as an example) (SYS-014) | Owner decision | Schedule settings, FPP schedule | Stage 3 | CDR-3 | Open |
| TBD-025 | Bedtime for the eye pods: when they switch off, and how (smart plug, Pi command to the projector, or FPP's schedule) (SYS-018; spec tree Q12) | Owner decision, then a Test with a real pod | Eye pod power design, INF power | Stage 1 | CDR-1 | Open |
| TBD-026 | Loudest acceptable sound level at the sidewalk, and how to measure it (SYS-030) | Owner decision, then a Measurement | Amp gain, FPP and operating-system volume caps | Stage 3 | CDR-3 | Open |
| TBD-027 | Brightness cap for the lips (SYS-031) | Owner decision, then a Test at the house | WLED brightness limit, power supply sizing | Stage 4 | CDR-4 | Open |
| TBD-028 | Door hold time: how long a visitor lost at the door still counts as present (SYS-047) | Owner decision, tuned in the Stage 0 simulator | Brain door-hold logic, theme settings | Stage 0 Step 4 | PDR | Open |
| TBD-029 | Where the real radar loses visitors near the door (sets the door zone) (SYS-047) | Measurement at the Stage 2 install | Door zone in the site config, fake radar's blind spot | Stage 2 (simulator uses a guess until then) | CDR-2 | Open |
| TBD-030 | How the radar tells coming from going, and the exact text of its messages. ESPHome's LD2450 page (checked 2026-11-09) gives speed in mm/s with no sign convention, and a per-target `direction` text sensor (`Approaching`, `Moving away`, `Stationary`) that would need a topic `shared/topics.py` doesn't have yet. It also doesn't state the state payload's number format (SYS-049, ICD-002) | Owner decision (use the `direction` sensor, which adds a topic), then a Test with the real ESP32 | How the brain tells coming from going; fake-radar parity | Stage 0 Step 3 (fake radar must match) | PDR | Open |
| TBD-031 | How much memory (RAM) the porch Pi has (architecture §3 doesn't say) | Owner decision at the Stage 3 purchase, using the budget check | Porch Pi memory budget (INF-009) | Stage 3 purchase | CDR-3 | Open |
| TBD-032 | Memory each program and the operating system use on a Pi | Measurement on a real Pi (with TBD-013) | Eye Pi and porch Pi memory budgets | Stage 1 (eye Pi), Stage 3 (porch Pi) | CDR-1 | Open |
| TBD-033 | Power the lip strips, extras and controller draw at the brightness cap | Analysis, after TBD-007 (lengths) and TBD-027 (cap) | Lip supply budget (MTH-009) | Stage 4 purchase | CDR-4 | Open |
| TBD-034 | How each end-to-end time (SYS-019 to SYS-023, SYS-029) is shared between the hops on its path | Analysis with a latency model (each hop's estimated or measured delay, added up per path like `tools/reqs/budget.py`), built while burning down TBD-020 to TBD-023 (owner, 2026-11-09); then a Measurement in the Stage 0 simulator and again on hardware. It gives the timing requirements their `basis` | Per-hop budgets in the ICDs' timing sections ([timing-budgets.md](requirements/timing-budgets.md)) | Stage 0 Step 4 | PDR | Open |
| TBD-035 | How the lips' idle "breathe" color follows the theme (a WLED preset per theme, chosen by the brain or by FPP) | Owner decision, then a Test with WLED | MTH-001, theme format (ICD-005) | Stage 4 | CDR-4 | Open |
| TBD-036 | Whether Falcon Player can run on the porch Pi 5 next to the brain and Mosquitto (FPP's own OS image vs Raspberry Pi OS) | Verify against FPP's documentation, then a Test | Porch Pi software setup (ICD-013), SYS-039 | Before the Stage 3 purchase | CDR-3 | Open |

## Closed

| ID | What was undecided | Closed by | Date |
|---|---|---|---|
| TBD-001 | How requirements, architecture and ICDs are documented | [ADR 0001](decisions/0001-requirements-and-architecture-format.md): Markdown + YAML with our own checker, SysML-ready (owner; [TS-001](trades/TS-001-requirements-approach.md)) | 2026-11-08 |
| TBD-002 | Eye renderer: Python + moderngl + pygame-ce, or Godot | [ADR 0002](decisions/0002-eye-renderer.md): Python + moderngl + pygame-ce (owner; [TS-002](trades/TS-002-eye-renderer.md), [results](trades/results/TS-002/README.md)) | 2026-11-08 |
