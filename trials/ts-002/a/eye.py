"""TS-002 trial, option A: the minimal eye in Python + moderngl + pygame-ce.

Throwaway trial code: nothing outside trials/ts-002/ may import it.

Run from the repository root with the trial venv:
    trials/ts-002/.venv/bin/python trials/ts-002/a/eye.py [--mirror] [--rotate90] [--gles]
                                                          [--bench 60] [--mqtt]
Keys: 1-6 expressions, space blinks, Esc quits. Mouse moves the gaze.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import struct
import sys
import time
from pathlib import Path

import moderngl
import pygame

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))          # repository root, for shared.topics
from shared import topics  # noqa: E402

# Expression table from docs/architecture.md §2 / eye-sketch.html.
MOODS = {
    "neutral":   dict(open=1.0,  low=0.0,  curve=0.0, pupil=1.0,  spark=0.0),
    "happy":     dict(open=0.9,  low=0.38, curve=1.0, pupil=1.15, spark=0.0),
    "sparkle":   dict(open=0.95, low=0.3,  curve=1.0, pupil=1.3,  spark=1.0),
    "surprised": dict(open=1.15, low=0.0,  curve=0.0, pupil=0.65, spark=0.0),
    "sleepy":    dict(open=0.42, low=0.08, curve=0.0, pupil=0.9,  spark=0.0),
    "asleep":    dict(open=0.0,  low=0.05, curve=0.0, pupil=1.0,  spark=0.0),
}
EXPRESSION_RATE = -math.log(1 - 0.12) * 60   # the sketch eases 12% per 60 fps frame
GAZE_RATE = -math.log(1 - 0.2) * 60          # and the gaze 20% per frame
BLINK_S = 0.2


class EyeState:
    """Expression easing, gaze smoothing, wandering and blinks (same rules as the sketch)."""

    def __init__(self) -> None:
        self.now = 0.0
        self.cur = dict(MOODS["neutral"])
        self.target = dict(MOODS["neutral"])
        self.gaze = [0.0, 0.0]
        self.gaze_target = [0.0, 0.0]
        self.last_aim = -1e9
        self.next_wander = 0.0
        self.next_blink = 2.5
        self.blink_start = -1.0

    def set_expression(self, name: str) -> None:
        if name in MOODS:
            self.target = dict(MOODS[name])

    def aim(self, x: float, y: float) -> None:
        """x, y in sketch space (300 x 400)."""
        clamp = lambda v: max(-1.0, min(1.0, v))  # noqa: E731
        self.gaze_target = [clamp((x - 150) / 170) * 46, clamp((y - 200) / 220) * 88]
        self.last_aim = self.now

    def blink(self) -> None:
        if self.blink_start < 0:
            self.blink_start = self.now

    def update(self, dt: float) -> float:
        """Advance by dt seconds; returns the blink factor (1 = open)."""
        self.now += dt
        k = 1 - math.exp(-EXPRESSION_RATE * dt)
        for key in self.cur:
            self.cur[key] += (self.target[key] - self.cur[key]) * k
        if self.now - self.last_aim > 2.5 and self.now > self.next_wander:
            self.gaze_target = [random.uniform(-40, 40), random.uniform(-60, 60)]
            self.next_wander = self.now + random.uniform(1.2, 3.0)
        g = 1 - math.exp(-GAZE_RATE * dt)
        for i in (0, 1):
            self.gaze[i] += (self.gaze_target[i] - self.gaze[i]) * g
        if self.now > self.next_blink and self.target["open"] > 0.2:
            self.blink()
        factor = 1.0
        if self.blink_start >= 0:
            t = (self.now - self.blink_start) / BLINK_S
            if t >= 1:
                self.blink_start = -1.0
                self.next_blink = self.now + random.uniform(2.5, 6.0)
            else:
                factor = abs(1 - 2 * t)
        return factor


def start_mqtt(state: EyeState, side: str):
    """Obey monster/eyes/blink and /expression; publish online/offline with a last will."""
    from shared.mqtt_client import connect, new_client

    status = topics.eye_status(side)
    client = new_client(f"ts002-eye-{side}")
    client.will_set(status, "offline", retain=True)

    def on_connect(c, *_):
        c.subscribe([(topics.EYES_BLINK, 0), (topics.EYES_EXPRESSION, 0)])
        c.publish(status, "online", retain=True)

    def on_message(_c, _u, msg):
        try:
            data = json.loads(msg.payload)  # TBD-003: plain JSON until schemas exist
        except ValueError:
            return                          # fail friendly: ignore bad messages
        if msg.topic == topics.EYES_BLINK:
            state.blink()
            print(f"mqtt: blink {data}", flush=True)
        elif msg.topic == topics.EYES_EXPRESSION:
            state.set_expression(str(data.get("name", "")))
            print(f"mqtt: expression {data}", flush=True)

    client.on_connect = on_connect
    client.on_message = on_message
    connect(client)
    client.loop_start()
    return client


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", default="1280x720")
    ap.add_argument("--eye-size", type=float, default=0.9)
    ap.add_argument("--mirror", action="store_true")
    ap.add_argument("--rotate90", action="store_true")
    ap.add_argument("--gles", action="store_true", help="ask for an OpenGL ES 3.0 context, like the Pi")
    ap.add_argument("--bench", type=float, default=0, help="run N seconds, cycle expressions, print timing")
    ap.add_argument("--mqtt", action="store_true")
    ap.add_argument("--no-vsync", action="store_true", help="draw as fast as possible (measures cost per frame)")
    ap.add_argument("--screenshot", help="save the last frame to this PNG file")
    ap.add_argument("--expression", default="neutral", help="starting expression")
    ap.add_argument("--fps-cap", type=int, default=0, help="limit frames per second in software (0 = off)")
    args = ap.parse_args()
    width, height = (int(v) for v in args.size.split("x"))

    pygame.init()
    if args.gles:
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_ES)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 0)
    pygame.display.set_mode((width, height), pygame.OPENGL | pygame.DOUBLEBUF, vsync=0 if args.no_vsync else 1)
    pygame.display.set_caption("TS-002 option A: Python + moderngl")
    ctx = moderngl.create_context(require=310)   # the Pi 5 offers OpenGL 3.1 / GLES 3.1
    print("GL:", ctx.info["GL_VERSION"], "|", ctx.info["GL_RENDERER"], flush=True)

    prog = ctx.program(
        vertex_shader="#version 300 es\nin vec2 pos;\nvoid main() { gl_Position = vec4(pos, 0.0, 1.0); }\n",
        fragment_shader=(HERE / "eye.frag").read_text(),
    )
    quad = ctx.buffer(struct.pack("8f", -1, -1, 1, -1, -1, 1, 1, 1))   # two triangles covering the window
    vao = ctx.vertex_array(prog, [(quad, "2f", "pos")])
    prog["u_window"].value = (width, height)
    prog["u_eye_size"].value = args.eye_size
    prog["u_mirror"].value = args.mirror
    prog["u_rotate90"].value = args.rotate90

    state = EyeState()
    state.set_expression(args.expression)
    client = start_mqtt(state, "left") if args.mqtt else None
    names = list(MOODS)
    clock = pygame.time.Clock()
    frame_times: list[float] = []
    start = last = time.perf_counter()
    next_mood = 3.0
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                state.blink()
            elif event.type == pygame.KEYDOWN and pygame.K_1 <= event.key <= pygame.K_6:
                state.set_expression(names[event.key - pygame.K_1])
            elif event.type == pygame.MOUSEMOTION:
                # Mouse pixel -> sketch space (rotation/mirroring ignored in the trial).
                scale = min(width / 300, height / 400) * args.eye_size
                state.aim((event.pos[0] - width / 2) / scale + 150, (event.pos[1] - height / 2) / scale + 200)

        now = time.perf_counter()
        dt, last = now - last, now
        frame_times.append(dt)
        if args.bench:
            if now - start > next_mood:          # cycle expressions every 3 s
                state.set_expression(names[int(next_mood / 3) % len(names)])
                next_mood += 3.0
            if now - start > args.bench:
                running = False

        blink = state.update(dt)
        prog["u_gaze"].value = tuple(state.gaze)
        prog["u_open"].value = state.cur["open"] * blink
        for key in ("low", "curve", "pupil", "spark"):
            prog[f"u_{key}"].value = state.cur[key]
        ctx.clear()
        vao.render(moderngl.TRIANGLE_STRIP)
        pygame.display.flip()
        if args.fps_cap:
            clock.tick(args.fps_cap)

    if client:
        # On a clean exit the broker doesn't send the last will, so say "offline" ourselves.
        client.publish(topics.eye_status("left"), "offline", retain=True).wait_for_publish(2)
        client.disconnect()
    if args.screenshot:                       # draw once more and read it before the swap
        ctx.clear()
        vao.render(moderngl.TRIANGLE_STRIP)
        data = ctx.fbo.read(components=4)   # GLES only guarantees RGBA read-back
        pygame.image.save(pygame.transform.flip(pygame.image.frombytes(data, (width, height), "RGBA"), False, True), args.screenshot)
    if args.bench:
        report(frame_times[30:] if len(frame_times) > 60 else frame_times)  # skip start-up frames
    pygame.quit()
    return 0


def report(times: list[float]) -> None:
    ms = sorted(t * 1000 for t in times)
    if not ms:
        print("no frames recorded", flush=True)
        return
    worst1 = ms[int(len(ms) * 0.99)]
    print(json.dumps({
        "frames": len(ms),
        "mean_fps": round(1000 / (sum(ms) / len(ms)), 2),
        "p99_frame_ms": round(worst1, 2),
        "max_frame_ms": round(ms[-1], 2),
        "mean_frame_ms": round(sum(ms) / len(ms), 3),
        "hitches_over_25ms": sum(1 for v in ms if v > 25),
    }), flush=True)


if __name__ == "__main__":
    sys.exit(main())
