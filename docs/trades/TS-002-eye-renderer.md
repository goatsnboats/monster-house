# TS-002 — Eye renderer: Python + moderngl, or Godot

> **Status:** Evaluating · **Date:** 2026-11-08 · **Decides:** what the eye renderer is built with · **TBD:** TBD-002 · **ADR:** — · **Affects:** Stage 0 Step 2 (and every later step that touches the eyes); TBD-003 (message schemas); TBD-013 (buy a Pi early?); `shared/topics.py`

Status moves through `Framing` → `Awaiting weights` (Stop 1) → `Evaluating` →
`Recommended` (Stop 2) → `Decided (owner, YYYY-MM-DD, <where>)`.

## 1. Question
Should the eye renderer be written in Python with OpenGL shaders (`moderngl` for
drawing, `pygame-ce` for the window), or in the Godot game engine?

## 2. Context

- **What depends on it:**
  - All of Stage 0 Step 2: the full eye, expressions, blinks, per-eye config and MQTT
    control are built in whatever this study picks.
  - **TBD-003, message schemas.** If the renderer isn't Python, schemas (and topic names)
    must be defined somewhere both languages can read. See *Couplings* below.
  - **TBD-013, whether to buy a Pi 5 early.** The "path to Pi" evidence here can only be
    *documented* until a Pi exists; this study says what a Pi would measure.
  - Stage 0 Step 8 (Pi setup script) and Stage 1 (first eye pod) install whatever is picked.
- **Constraints and owner direction:**
  - `CLAUDE.md` (eye renderer constraints): drawn on the GPU; shaders compatible with
    OpenGL ES 3.0 / GLSL ES 3.00; 60 fps; runs in a desktop window for development and
    full-screen without a desktop environment (KMS/DRM) on the Pi; rotation 0/90°,
    horizontal mirroring, per-eye placement; expressions are numbers that ease; never
    show an error on screen; configuration in YAML; themes are data.
  - Architecture §2: Pi 5 with **1 GB** RAM per eye pod; the projector's native
    resolution (720p is plenty).
  - Stage 0 plan, Step 2: build "the same minimal eye (sclera, iris, pupil, lids) two
    ways" in about a day, compare smoothness, ease of iterating on the look, and the path
    to Pi 5; the owner picks.
  - `CLAUDE.md` (coding conventions): plain, readable code for an owner who isn't a
    full-time developer; ask before adding heavy dependencies.
- **Couplings (what this decision constrains):**
  - **Topic names.** They live in `shared/topics.py`, and a test enforces that. A Godot
    renderer can't import Python, so topics would need a neutral source (e.g. a YAML
    file that Python and GDScript both read, or code generated from it), and the
    hard-coded-topic test would need to cover GDScript too.
  - **Message schemas (TBD-003).** Same issue: a non-Python renderer pushes TBD-003 toward
    a language-neutral format such as JSON Schema.
  - **Config in YAML.** Python reads YAML with PyYAML (already pinned). Godot has no
    built-in YAML reader, so it would need an add-on or JSON.
  - **Tests.** Gaze-angle math runs inside each eye. In Python it's tested with `pytest`
    like everything else; in Godot it needs a second test setup.
  - **No requirements baseline yet.** ADR 0001 set the format, but no `EYE-` requirements
    exist yet, so criteria trace to `CLAUDE.md` and architecture §2 for now.
- **Deadline:** Stage 0 Step 2 is planned for November 2026; nothing in Step 2 beyond the
  trial can start until this is decided.
- **Cost to reverse:** low now, rising fast. After the trial only throwaway code exists.
  After Step 2 the full eye, its config handling and its MQTT wiring would be rewritten
  (estimated 1–2 weeks of sessions, judgment). After Stage 1 the Pi setup and service
  files change too.

## 3. Criteria

### Gates (must pass)
| ID | Gate | How checked | Traces to |
|---|---|---|---|
| G1 | Draws on the GPU, with shaders that compile as GLSL ES 3.00 | Trial shaders compiled with a GLSL ES 3.00 validator; documentation for the engine's own shaders | `CLAUDE.md` renderer constraints; arch §2 |
| G2 | A documented way to run full-screen on Raspberry Pi OS Lite (64-bit, Bookworm) on a Pi 5 **without a desktop environment** | Documentation now; measured once a Pi exists (TBD-013). A single-app kiosk compositor (e.g. `cage`) passes this gate but scores lower on C2 | `CLAUDE.md`; arch §2 |
| G3 | Runs in a window on the Ubuntu 24.04 desktop | Measured in the trial | `CLAUDE.md` |
| G4 | Can subscribe and publish MQTT, including a last-will status message | Documentation, then the trial | `CLAUDE.md` architecture rules; arch §2–3c |
| G5 | Free and open source, with no per-device licence | Documentation | Stage 0 cost: $0 |

### Weighted criteria
| ID | Criterion | Weight | How measured | 1 = | 3 = | 5 = |
|---|---|---|---|---|---|---|
| C1 | **Smoothness** | 20 | Trial on the desktop: 60 s run of the minimal eye at 1280×720 with the pupil gliding and lids blinking; mean fps, worst 1% frame time, visible stutter | Visible stutter, or below 55 fps mean | Steady 60 fps with occasional (< 1 per minute) hitches | Locked 60 fps, worst 1% frame under 20 ms, no visible hitches |
| C2 | **Path to Pi 5** (GLES 3.0, no desktop, 1 GB RAM) | 25 | Documented now (GL/GLES version needed vs. the Pi 5 driver; KMS/DRM support; memory use measured on the desktop as a proxy). Measured on a Pi later | Needs workarounds nobody documents, or likely over ~400 MB of RAM | Works through a documented but extra layer (e.g. a kiosk compositor, or a settings change), modest RAM | Documented to run directly on KMS/DRM with GLES 3.0, small RAM use, others report running it on a Pi 5 |
| C3 | **Ease of iterating on the look** | 15 | Trial: time to change a shape, colour or easing and see it; whether shaders/parameters reload while running; how closely the minimal eye matches `eye-sketch.html` for the effort | Edit, rebuild, restart for every tweak; hard to match the sketch | Restart in a few seconds; matching the sketch takes some fiddling | Live reload or live editor; the sketch's shapes carry over directly |
| C4 | **Readable by the owner** | 15 | Trial code read side by side: size, how many concepts, one language or two in the repo (judgment, owner can check) | Two languages plus engine-specific concepts; hard to follow | A second language or an engine editor, but each part is short and clear | Same language as the rest of the repo; short, plain files |
| C5 | **Fits the rest of the system** | 15 | Can it use `shared/topics.py`, YAML config, `paho-mqtt` and `pytest` as they are? (See *Couplings*) | Needs parallel copies of topics, config and tests in another language | Needs one shared neutral file (e.g. topics/schemas in YAML) plus small adapters | Uses the existing shared code, config and tests directly |
| C6 | **Setup and deploy effort** | 10 | Steps and download size to install on the desktop and on a fresh Pi; how it runs as a system service | Manual builds, large downloads, fragile service setup | A few documented steps; one sizeable download | `pip install` from pinned requirements, or one small binary; standard service file |

Weights total 100. **Set by the owner on 2026-11-08, in session (Stop 1): the proposed weights were accepted unchanged.**

**Why these weights:**
- **C2 Path to Pi (25):** the whole point of Stage 0 is code that's ready for the Pi. A
  renderer that can't run well on a 1 GB Pi without a desktop is wasted work, and it's the
  part we can't measure yet.
- **C1 Smoothness (20):** the eyes must look alive; stutter is the most visible failure.
  Both options will probably manage 60 fps on a desktop, so it may not separate them much.
- **C3 Look iteration (15):** the eyes' look will be tuned many times (Step 2, the house
  preview, every theme), so a fast loop saves real hours.
- **C4 Readable (15):** the owner reads the code and isn't a full-time developer.
- **C5 Fits the system (15):** one-brain-many-limbs over MQTT works with either option, but
  sharing topics, config and tests avoids two copies drifting apart.
- **C6 Setup (10):** done once per machine, and scripted in Step 8.

## 4. Options

### Screened out
| Option | Reason |
|---|---|
| Plain `pygame` drawing on the CPU | Fails G1. `CLAUDE.md` and arch §2 rule out per-frame CPU drawing on the Pi. |
| C or C++ with SDL2 + OpenGL ES directly | Same GPU path as A, but dominated by A on C4 (the owner reads the code) and C5 (no shared Python code). |
| Python + raylib bindings | A close cousin of A (Python driving the GPU through its own window layer). Judgment: A gives direct control of GLSL shaders and is the plan's named candidate. **Fallback** if A's Pi path (G2) turns out weak; raylib's Pi/DRM support would then be checked. |
| Web page in a kiosk browser (WebGL) | Attractive because `eye-sketch.html` is already SVG. Judgment: a browser plus a compositor is the heaviest option on a 1 GB Pi, and adds a third language. **Fallback** if both shortlisted options fail. |
| Other engines and languages (LÖVE/Lua, Rust/Bevy, Unity) | Judgment: a new language without Godot's visual editor (LÖVE, Bevy), or not open source (Unity, fails G5). |
| `pi3d` (Python 3D library for the Pi) | Judgment: built around older Raspberry Pi display paths. Worth checking only if the owner wants it considered. |

### Shortlist
**A — Python + `moderngl` + `pygame-ce`.** The eye is drawn by GLSL fragment shaders
(shapes as smooth signed-distance fields), controlled by a small Python program that
also handles MQTT (`paho-mqtt`), YAML config and easing. On the Pi, `pygame-ce` would
open a full-screen surface through SDL's KMS/DRM driver. Everything stays in one
language, with `pytest` for the math. The main question to check is whether `moderngl`'s
OpenGL requirements match what the Pi 5's GPU driver offers.

**B — Godot 4 (GDScript, Compatibility renderer).** The eye is a Godot scene: shapes or
shaders in the editor, animation by tweens, logic in GDScript (a Python-like language).
MQTT via a GDScript add-on, or a tiny Python helper that forwards messages. On the Pi,
Godot exports an arm64 Linux build. The main questions to check are its GLES 3.0
support and how it gets a full-screen output without X11 or a desktop (likely through a
kiosk Wayland compositor).

## 5. Evidence
*Not started. Gathered after Stop 1.*

Planned trial (about a day, throwaway code in `trials/ts-002/`, imported by nothing):
- The **same minimal eye** both ways: sclera, iris, pupil, upper and lower lids with the
  lower-lid smile, bold outline, catchlight.
- Pupil glides after the mouse; keys switch `neutral` ↔ `happy` with easing and trigger a blink.
- A 1280×720 window, with mirroring and 90° rotation switches.
- Logs fps and frame times for 60 s; records memory use.
- Receives `monster/eyes/blink` over MQTT from the Step 1 debug tool, to prove G4.

Planned documented checks (sources and dates recorded at the time): the GL/GLES versions
each needs vs. the Pi 5's Mesa V3D driver; KMS/DRM support; arm64 builds; MQTT options for Godot.

**What a Pi would measure later (TBD-013):** fps and memory at 720p full-screen on
Pi OS Lite, start-up time from boot, and whether the no-desktop path works as documented.

## 6. Scores
*Not run. Scoring waits for the owner's weights (Stop 1).*

## 7. Sensitivity
*Not run.*

## 8. Recommendation
*Not run.*

## 9. Decision
*Open.*

## Links
- Stage 0 plan, Step 2: [`../stage-0-plan.md`](../stage-0-plan.md)
- Architecture §2 (eye pods): [`../architecture.md`](../architecture.md)
- Visual reference: [`../reference/eye-sketch.html`](../reference/eye-sketch.html)
- TBD register row: TBD-002 (the register lives on the `process/trade-study` branch until it merges)
- Related: TS-001 and ADR 0001 (requirements format), TBD-003 (message schemas), TBD-013 (early Pi)
