# Stage 0 — Software Prototype on the Desktop

_Goal: by late February, see the whole monster working in software (both eyes on a photo of the house, reacting to pretend visitors) with code ready to copy onto Raspberry Pis. Cost: $0._

Built with Claude Code. Each step below is one Claude Code task (or a few sessions). Tick the boxes as you go.

## Prep (owner)
- [ ] Measure both windows: glass width × height, any fixed dividers, and the floor space behind each.
- [ ] Note the desktop's operating system.
- [ ] Install Git, Python 3.11+, Mosquitto and Claude Code on the desktop.
- [ ] Create a private GitHub repository `monster-house`, and add this starter kit.

## Step 1 — Project setup (November)
- [x] Folder layout per `docs/architecture.md` §10. One Python virtual environment and a dependency file.
- [ ] `shared/`: MQTT topic names and payload schemas (dataclasses or pydantic) for everything in architecture §2–3c.
  _Topic names done (`shared/topics.py`). Payload schemas wait for TBD-003._
- [ ] Mosquitto running locally, with a config file in `deploy/`.
  _Config and run script done (`deploy/mosquitto/`) and tested with Mosquitto 2.0.22. Tick once Mosquitto is installed on the desktop (owner: needs sudo)._
- [x] A tiny helper to publish and subscribe from the command line, for debugging.

**Done when:** a test message published by one program arrives in another through Mosquitto, using the shared schemas, and `pytest` runs green.

## Step 2 — Eye renderer, first version (November)
- [x] **Renderer trial (about a day):** Build the same minimal eye (sclera, iris, pupil, lids) two ways, as Python + OpenGL shaders (`moderngl` + `pygame-ce` window) and as Godot. Compare smoothness, ease of iterating on the look, and the path to Pi 5 (GLES 3.0, no desktop environment, low memory). Write up the recommendation, and the owner picks one.
  _Done 2026-11-08: [TS-002](trades/TS-002-eye-renderer.md) ([results](trades/results/TS-002/README.md)). The owner chose Python + moderngl + pygame-ce ([ADR 0002](decisions/0002-eye-renderer.md))._
- [ ] Full eye matching `docs/reference/eye-sketch.html`: layers, bold outline, catchlight, sparkle, lids with the lower-lid smile.
- [ ] Expressions from the table in architecture §2, eased smoothly. Blinks on command, plus a fallback timer.
- [ ] Per-eye config: window size, eye placement, rotation 0/90°, mirroring, brightness.
- [ ] Listens to `monster/eyes/*` and `monster/theme`; publishes its online/offline status.

**Done when:** two eye windows open on the desktop, each shaped like its real window. They blink, change expression on command, and glide to look-at points sent over MQTT, at a steady 60 fps.

## Step 3 — Pretend visitors / fake radar (December)
- [ ] A top-down view of the walk, steps and sidewalk (rough dimensions, adjustable).
- [ ] Drag up to 3 "kids" with the mouse. Add/remove kids.
- [ ] Publishes exactly the topics and units ESPHome's LD2450 component will (mm, radar-relative), at about 10 Hz.

**Done when:** dragging a kid makes both eyes follow, using placeholder gaze math.

## Step 4 — Monster brain, first version (December)
- [ ] Mood state machine: Asleep → Waking → Greeting → Watching → Goodbye (see architecture §3b), with timings from the theme settings.
- [ ] Gaze: radar to house coordinates, smoothing, focus-target choice (new arrival wins, hold 3–6 s, closest breaks ties), and per-eye angle math with parallax.
- [ ] Brain-owned blinks (both eyes together).
- [ ] Clip pools with no-repeat shuffling and a minimum gap between lines.
- [ ] Fake FPP: logs clip triggers and plays placeholder audio files through the desktop speakers. It reports "clip finished" like FPP will.
- [ ] Failure behavior: radar missing → ambient mode; eye missing → keep going.
- [ ] Tests for mood transitions, gaze math and clip pools.

**Done when:** a pretend visit plays through from asleep to goodbye and back to sleep, and it *feels* right to the owner.

## Step 5 — House preview (January)
- [ ] The live eyes composited onto `docs/reference/house-front.jpg` at the two window positions (positions adjustable by dragging corners).
- [ ] A simple glowing line where the lips will go (porch roof edge and railing), so the whole face reads.

**Done when:** the owner can decide lopsided vs. matched eyes, eye size and colors by looking at it.

## Step 6 — Phone buttons (January)
- [ ] A small web page served by the brain on the home network: great costume (sparkle + compliment), burp, sing, mute voice, sleep now, wake now, and current mood.

**Done when:** pressing a button on a phone changes the monster within half a second.

## Step 7 — Content (owner, in parallel)
- [ ] Monster's name.
- [ ] Eye art direction: colors, iris style, outline weight.
- [ ] Rough voice lines recorded on a phone (yawn, 5 greetings, 5 comments, 2 goodbyes, costume compliments, burp), dropped into `themes/halloween/audio/`.

## Step 8 — Ready for the Pi (February)
- [ ] A setup script that turns a fresh Raspberry Pi OS Lite (64-bit) install on a Pi 5 (1GB) into an eye pod: dependencies, renderer as a system service, full-screen on KMS/DRM, cursor hidden, starts at boot.
- [ ] A first-install checklist for the one-eye test (projector, screen, mask, shroud, mirroring, rotation).

**Done when:** the setup is documented well enough to run the moment the Pi arrives.

## Exit criteria for Stage 0 (then buy Stage 1 parts)
- [ ] The owner likes the eyes in the house preview.
- [ ] Pretend visits feel right.
- [ ] Eye layout decided (lopsided or matched; rotation for each window).
- [ ] Windows measured; projector model chosen (AAXA P400 class, or the fallback).
