# 0002 — Eye renderer: Python + moderngl + pygame-ce

> **Status:** Accepted (owner, 2026-11-08, in session) · **Date:** 2026-11-08 · **Deciders:** owner · **Supersedes:** — · **Trade study:** [TS-002](../trades/TS-002-eye-renderer.md)

## Context
Each eye is drawn live on the GPU and must run in a desktop window now and full-screen
without a desktop on a 1 GB Raspberry Pi 5 later. The Pi 5's GPU offers OpenGL ES 3.1
and desktop OpenGL 3.1. The rest of the system is Python talking MQTT, with topic names
in `shared/topics.py`, configuration in YAML and tests in `pytest`.

A one-day trial built the same minimal eye both ways. Both held 60 fps with no hitches
on the desktop. Python + moderngl used about a third less memory (about 150 MB vs 217 MB) and
similar CPU (4.0–5.2 % vs 4.7–5.9 % of one core), and could use the shared Python code directly. Godot
has no direct KMS/DRM output, so on the Pi it would need a compositor such as `cage`.
Neither option has run on a real Pi 5 yet.

## Decision
We will build the eye renderer in **Python 3.11 with `moderngl` (requesting OpenGL
3.1-level, `require=310`) for drawing and `pygame-ce` (SDL) for the window**. Shaders
are written in GLSL ES 3.00. On the Pi, it runs full-screen through SDL's KMS/DRM
driver with no desktop or compositor.

## Consequences
- **Easier:**
  - One language across brain, eyes and simulators.
  - The eyes import `shared/topics.py` and the shared MQTT helper.
  - Gaze and easing math is tested with `pytest` like everything else.
  - TBD-003 (message schemas) can stay Python-first.
- **Harder:**
  - There is no visual editor, so Step 2 should add reloading of the shader and theme
    values while the eye runs.
  - The Pi has to compile `moderngl` and `glcontext` (there are no ARM64 wheels), so
    the Step 8 setup script installs build tools and X11/GL headers (or uses
    Bookworm's `python3-moderngl` 5.7.4).
- **Must stay true:**
  - Shaders use only GLSL ES 3.00 features.
  - The context request stays at `require=310` or lower.
  - Pixel read-back uses RGBA (RGB returns garbage on OpenGL ES).
- **Open risk:** behaviour on the real Pi 5 V3D driver is still unmeasured (TBD-013).
  If it fails there, revisit with TS-002's fallbacks (Python + raylib, or Godot).

## Alternatives considered
- **Godot 4 (GDScript, Compatibility renderer):** has the best live editing for the look,
  but needs a compositor on the Pi, uses more memory, and duplicates topic names,
  config handling and tests outside Python. It sometimes failed to exit in the trial.
- **Screened out earlier:** CPU drawing with pygame, C/C++, Python + raylib (kept as a
  fallback), a browser kiosk (kept as a fallback), other engines, and `pi3d`.

## Links
- Trade study: [TS-002](../trades/TS-002-eye-renderer.md); results report: [results/TS-002](../trades/results/TS-002/README.md); trial code in `trials/ts-002/`
- Owner's decision: 2026-11-08, in the Claude Code session, after reviewing the Stop 2 recommendation ("Option a sounds good"). Recorded in the commit that marks this ADR Accepted.
