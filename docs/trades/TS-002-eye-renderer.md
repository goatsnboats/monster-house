# TS-002 — Eye renderer: Python + moderngl, or Godot

> **Status:** Decided (owner, 2026-11-08, in session) · **Date:** 2026-11-08 · **Decides:** what the eye renderer is built with · **TBD:** [TBD-002](../TBD.md) (closed) · **ADR:** [0002](../decisions/0002-eye-renderer.md) (Accepted) · **Results:** [report](results/TS-002/README.md) · **Affects:** Stage 0 Step 2 (and every later step that touches the eyes); TBD-003 (message schemas); TBD-013 (buy a Pi early?); `shared/topics.py`

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
| G3 | Runs in a window on the Ubuntu desktop (26.04.1 LTS, measured; the framing wrongly said 24.04) | Measured in the trial | `CLAUDE.md` |
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

**Trial set-up (2026-11-08).** The same minimal eye was built both ways in
[`trials/ts-002/`](../../trials/ts-002/README.md): sclera, iris and ring, pupil,
catchlights, sparkle, both lids with the lower-lid smile, and the bold outline. It has
the expression table, gaze easing, wandering, blinks, mirroring, 90° rotation, and MQTT
control. Both versions use the **same shader math**: the Godot shader is a line-for-line
copy, and only the entry point and output names differ. The screenshots match
([`results/compare-a-top-b-bottom.png`](../../trials/ts-002/results/compare-a-top-b-bottom.png)).

**Machine:** the owner's desktop, Ubuntu 26.04.1 LTS (Intel Arrow Lake graphics, Mesa 26.0.8, 24 cores),
Python 3.11.18, moderngl 5.13.0, pygame-ce 2.5.8 (SDL 2.32.10), Godot 4.7.2.

**Full results report** with every figure, log and the scripts that regenerate them: [results/TS-002](results/TS-002/README.md). The numbers below combine the first, hand-run session with the scripted re-run (`trials/ts-002/run_trials.py`) the same day.

**Limit on the smoothness tests:** Claude runs in the `dev` account, whose desktop
session isn't on a monitor. The compositor slows down windows nobody can see (with vsync
on, A got about 20 fps), so **frame pacing on a real 60 Hz screen was not measured**.
Instead, both options ran with vsync off and a 60 fps software cap (smoothness and CPU
use), and uncapped (cost per frame). The owner can check a visible screen with the
commands in the trial README.

| # | Option | Criterion | Finding | Kind | Source |
|---|---|---|---|---|---|
| E1 | A | C1 | At a 60 fps cap, OpenGL ES context, 1280×720: 62 fps, worst 1% frame 16.9 ms, **0 frames over 25 ms** in 2 × 27 s runs | measured | `measure.sh` + `eye.py --bench 27 --no-vsync --fps-cap 60 --gles`, desktop, Wayland |
| E2 | B | C1 | Same test: 60.0 fps, worst 1% frame 16.9 ms, **0 frames over 25 ms** in 2 × 27 s runs | measured | `measure.sh` + Godot `--rendering-driver opengl3_es -- --bench 27 --no-vsync --fps-cap 60` |
| E3 | A | C1, C2 | Uncapped: **0.25 ms per frame** on average (about 3,900 fps), 0 hitches | measured | `eye.py --bench 8 --no-vsync`, Wayland |
| E4 | B | C1, C2 | Uncapped: **3.0–3.2 ms per frame** (about 320 fps on OpenGL ES), worst frame about 7 ms every run. This includes Godot's engine loop and compositor pacing, not only drawing | measured | Godot `-- --bench 8 --no-vsync`, 3 runs |
| E5 | A, B | C2 | At 60 fps, over 4 runs each in two sessions: **CPU A 4.0–5.2 % vs B 4.7–5.9 %** of one core (similar; A a little lower on average); **memory A 147–153 MB vs B 217–218 MB** (consistent). Desktop memory includes the Intel driver, so Pi figures will differ; the comparison is fair | measured | `measure.sh` and `run_trials.py`, 20 s samples from `/proc`; [report](results/TS-002/README.md) |
| E6 | — | C2 | The Pi 5 GPU (Mesa V3D) offers **OpenGL ES 3.1** (conformant) and **desktop OpenGL 3.1** (not conformant); no plans for 3.2 | documented | [Mesa V3D docs](https://docs.mesa3d.org/drivers/v3d.html); [Phoronix Pi 5 review](https://Phoronix.com/review/raspberry-pi-5-graphics); [FOSDEM 2025 talk](https://fosdem.org/schedule/event/BMFQSE-raspberry-pi-gpu-drivers-from-bookworm-to-trixie); checked 2026-11-08 |
| E7 | A | C2, G1 | `moderngl` asks for OpenGL 3.3 by default, but **runs with `require=310`** on a context capped at OpenGL 3.1 and on an **OpenGL ES 3.x context through EGL**, compiling `#version 300 es` shaders. Imitated on the desktop (`MESA_GL_VERSION_OVERRIDE=3.1`; SDL ES profile), **not on a Pi** | measured + documented | Probe scripts (2026-11-08); [moderngl context docs](https://moderngl.readthedocs.io/en/latest/reference/context.html) |
| E8 | A | C2 | On OpenGL ES, reading pixels back as RGB returns garbage; RGBA works. Matters only for screenshots | measured | Read-back probe, 2026-11-08 |
| E9 | A | C2, G2 | pygame-ce's bundled SDL 2.32.10 **includes the KMS/DRM driver** (it can't start here because the desktop owns the screen). Others run pygame-ce with `SDL_VIDEODRIVER=kmsdrm` on Pi OS Lite; older reports needed EGL driver overrides | measured + documented | SDL library symbols; [photobooth project](https://git.autonomic.zone/trav/nissaphotobooth/commit/f51f204a9deb96fcab959aa5fe159af6bbced1b3); [SDL Pi notes](https://wiki.libsdl.org/SDL3/README/raspberrypi); checked 2026-11-08 |
| E10 | B | C2, G2 | Godot 4.7.2 display drivers: **x11, wayland, headless only. No KMS/DRM.** On Pi OS Lite it needs a compositor (e.g. `cage`) or X. No source found showing Godot under `cage` on a Pi 5; one forum user reports Godot 4.6 running well on Pi OS **with** its desktop | measured + documented | `Godot --help`; [Godot Wayland/X11 docs](https://docs.godotengine.org/en/4.7/tutorials/platform/linux/wayland_x11.html); [Godot forum: Pi](https://forum.godotengine.org/t/godot-4-x-on-the-raspberry-pi/34417); checked 2026-11-08 |
| E11 | B | C2 | Godot **didn't exit after `quit()`** in 2 of about 12 launches in the first, hand-run session (it finished its work, then hung). In the scripted re-run it exited normally in all 15 launches. Seen only in the off-screen session; cause not investigated | measured | Trial runs, 2026-11-08; `run_trials.py` |
| E12 | A | C6 | **No Linux ARM64 wheels** for `moderngl` 5.13.0 or `glcontext` 3.1.0, so a Pi compiles them, which needs build tools and X11/GL headers (a source build here stopped at a missing `X11/Xlib.h`). `pygame-ce` 2.5.8 has a Pi wheel. Bookworm packages `python3-moderngl` 5.7.4 | measured + documented | [PyPI moderngl files](https://pypi.org/project/moderngl/5.13.0/#files); [Debian python-moderngl](https://sources.debian.org/src/python-moderngl/); checked 2026-11-08 |
| E13 | B | C6 | Godot is **one 146 MB program** (78 MB zip); an official `linux.arm64` build of 4.7.2 exists. On the Pi it also needs a compositor installed and configured | measured + documented | Download, 2026-11-08; [godotengine.org/download](https://godotengine.org/download/linux) |
| E14 | A, B | G1 | Both draw entirely on the GPU in a fragment shader. A's shader is plain `#version 300 es`; B's ran on Godot's `opengl3_es` driver | measured | Trial runs |
| E15 | A, B | G4, C5 | Both obey `blink` and `expression`, ignore a malformed message, publish `online`/`offline`, and the broker sends the **last will when the process is killed**. A uses `paho-mqtt` and `shared/topics.py`. B needed a hand-written MQTT client (82 lines) with the **topic names copied by hand**; an MIT add-on (godot-mqtt) exists. Godot reads `180` as `180.0` and logs an engine error for bad JSON | measured + documented | Trial runs with the Step 1 debug tool; [godot-mqtt](https://github.com/goatchurchprime/godot-mqtt) |
| E16 | A, B | C3 | Start-to-quit: **A 0.28–0.32 s, B 0.43–0.49 s** (6 runs each, two sessions), so both restart quickly after an edit. Godot's editor shows shader settings as live sliders (from tutorials; not tried here, because the editor needs a visible screen). A has no editor; shader reload while running could be added (judgment) | measured + documented | 3 timed runs each; [Godot shader tutorial](https://www.generalistprogrammer.com/tutorials/godot-4-shaders-tutorial) |
| E17 | A, B | C4 | Code size (non-blank, non-comment lines): A **204 Python + 69 shader**. B **164 GDScript + 82 MQTT + 68 shader + 24 scene/project**. A is in the repo's language; B adds GDScript, Godot's scene and node ideas, and its editor | measured + judgment | Line counts |
| E18 | B | C5 | Needs a neutral topic file (or generated code), its own test setup for gaze math, and an add-on or JSON for config (no built-in YAML) | judgment | See §2 *Couplings* |
| E19 | A, B | G5 | moderngl MIT, pygame-ce LGPL-2.1, Godot MIT: all open source, with no per-device fee | documented | Project licences, checked 2026-11-08 |

**Gates:** both options pass all five.
- **G2 passes narrowly for both.** For A, the parts are proven separately (SDL has KMS/DRM; moderngl runs at the Pi's GL level), but not together on a Pi. For B, it relies on an extra compositor that nobody documents with Godot on a Pi 5.
- **G4 passes for B** only with a hand-written client or a third-party add-on.

**What a Pi would measure (TBD-013):** A with `SDL_VIDEODRIVER=kmsdrm` and `require=310`
full-screen on Pi OS Lite; B under `cage`. Fps, memory and start-up for each, and
whether `moderngl` builds and runs on the V3D driver.

## 6. Scores
| Criterion | Weight | A: Python + moderngl | B: Godot 4 |
|---|---|---|---|
| C1 Smoothness | 20 | 5 (E1, E3) | 5 (E2) |
| C2 Path to Pi 5 | 25 | 4 (E5, E7, E9) | 3 (E4, E5, E10, E11) |
| C3 Look iteration | 15 | 4 (E16) | 5 (E16) |
| C4 Readable by the owner | 15 | 4 (E17) | 3 (E17) |
| C5 Fits the system | 15 | 5 (E15) | 2 (E15, E18) |
| C6 Setup and deploy | 10 | 3 (E12) | 3 (E13, E10) |
| **Weighted total (max 500)** | 100 | **425** | **355** |

Score notes:
- **C1:** both met the "5" description (60 fps, worst 1 % under 20 ms, no hitches), but
  only under a software cap with the window off screen. Provisional until checked on a
  visible screen. It doesn't separate the options either way.
- **C2:** A gets 4, not 5, because nothing has run on a real Pi 5 yet. B gets 3: it
  needs a compositor layer, uses about 70 MB more memory, and has the exit hang.
- **C4:** the shader math is the hardest part to read in both, so neither gets 5.

## 7. Sensitivity
B trails by 70 points. No single weight change can close that gap:
- **C3** is the only criterion where B leads, by one score step. Its weight would have
  to rise by 70 points.
- **Lowering a weight where A leads** isn't enough either. Setting C5 (A ahead by 3
  steps) to **zero** removes only 45 points; C2 to zero removes 25.
- **Only combinations flip it**, for example C5 to zero and C3 up by 25. That would mean
  sharing code with the rest of the system doesn't matter at all and a live editor
  matters most.

**Not close.** The result also holds if C2 is scored equal (A still leads by 45) or if
C1 is re-scored after a visible-screen check, since both options would move together.

**Narrow gates:** G2 for both options (see §5), and G4 for B.

## 8. Recommendation
**Option A: Python + `moderngl` + `pygame-ce`.**

- **Why:** it does the same job with a third less memory and similar CPU, stays in the repo's one
  language, and uses `shared/topics.py`, `paho-mqtt`, YAML and `pytest` directly. It
  also has a no-desktop path (SDL's KMS/DRM driver) that needs no extra compositor.
- **Main risks:**
  1. **Unproven on a real Pi 5.** `moderngl` at OpenGL 3.1 / ES 3.1 was only imitated
     on the desktop. If it misbehaves on the V3D driver, the fallback is the screened
     Python + raylib option, or Godot.
  2. **The Pi install compiles `moderngl`** (no ARM wheels): Step 8's setup script must
     install build tools and the X11/GL headers, or use Bookworm's older
     `python3-moderngl` 5.7.4.
  3. **No visual editor** for tuning the look. Mitigation: reload the shader and theme
     values while the eye runs (a small feature for Step 2).
- **What would change this recommendation:**
  - A Pi 5 test where `moderngl` can't create its context or draw correctly on V3D.
  - The owner deciding that tuning the look in a visual editor outweighs sharing code
    with the rest of the system (see §7).
  - A visible-screen check showing A stutters where Godot doesn't.
- **Cost to reverse:** low now (only trial code). By the end of Step 2, about 1–2 weeks
  of sessions (judgment), because the eye's logic would move to GDScript and topics and
  schemas would need a neutral file. **Buying one Pi 5 now (TBD-013)** would retire risk
  1 for about $45 before Step 2 builds on it.

## 9. Decision
**Decided by the owner on 2026-11-08, in the Claude Code session, after reading the Stop 2
recommendation: option A, Python + `moderngl` + `pygame-ce`.** Recorded in
[ADR 0002](../decisions/0002-eye-renderer.md) (Accepted).

- **Requirement allocations:** none yet (no `EYE-` requirements exist). When they're
  written, the eye renderer component is Python on `moderngl`/`pygame-ce`, deployed on
  the eye-pod Pi.
- **TBD register:** TBD-002 closed. TBD-003 no longer needs a language-neutral schema
  format for the renderer's sake. TBD-013 (buy a Pi 5 early) reopened, as the way to
  retire this decision's main risk.
- **Full results report**, with figures, logs and how to reproduce:
  [results/TS-002](results/TS-002/README.md).

## Links
- Stage 0 plan, Step 2: [`../stage-0-plan.md`](../stage-0-plan.md)
- Architecture §2 (eye pods): [`../architecture.md`](../architecture.md)
- Visual reference: [`../reference/eye-sketch.html`](../reference/eye-sketch.html)
- TBD register: [TBD-002](../TBD.md) (closed), TBD-003, TBD-013
- Results report: [results/TS-002](results/TS-002/README.md); ADR: [0002](../decisions/0002-eye-renderer.md)
- Related: TS-001 and ADR 0001 (requirements format), TBD-003 (message schemas), TBD-013 (early Pi)
