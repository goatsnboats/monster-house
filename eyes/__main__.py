"""Run one eye:  python -m eyes --side left

Opens a window shaped like that eye's real window and draws the eye. It obeys the
brain's messages over MQTT (ICD-001: look, expression, blink, theme) and announces
itself online/offline. Until the brain exists, send those by hand with
`python -m shared.mqtt_tool pub ...`, or use the keyboard and mouse:

    1-6     neutral, happy, sparkle, surprised, sleepy, asleep
    space   blink
    i       look around on its own (idle)
    mouse   look at the mouse
    Esc     quit

With no brain messages (or no broker) the eye wanders and blinks on its own, as it will
when the brain goes quiet (EYE-006).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time

from eyes.config import ConfigError, load_theme, load_window
from eyes.expressions import EXPRESSIONS
from eyes.link import EyeLink, apply
from eyes.render import SHAPES, EyeRenderer, offscreen, output_size
from eyes.state import EyeState
from shared.mqtt_client import DEFAULT_HOST, DEFAULT_PORT

log = logging.getLogger("eyes")


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="python -m eyes", description="Draw one monster eye.")
    ap.add_argument("--side", choices=["left", "right"], required=True, help="which window, as seen from the street")
    ap.add_argument("--theme", default="halloween")
    ap.add_argument("--long-side", type=int, default=720, help="window's long side in pixels (desktop window)")
    ap.add_argument("--projector", action="store_true",
                    help="draw exactly what the projector shows (rotated and mirrored), not the street view")
    ap.add_argument("--shape", choices=SHAPES, default=None,
                    help="override the site config's eye_shape for this run: square (fills the glass), "
                         "oval (the sketch) or stretch (oval shaped like the window)")
    ap.add_argument("--fullscreen", action="store_true", help="full screen, cursor hidden (as on the Pi)")
    ap.add_argument("--expression", default="neutral", choices=list(EXPRESSIONS))
    ap.add_argument("--no-vsync", action="store_true", help="draw as fast as possible (to measure cost per frame)")
    ap.add_argument("--seconds", type=float, default=0, help="quit after this many seconds and print frame timing")
    ap.add_argument("--screenshot", metavar="PNG", help="draw one frame offscreen, save it and quit (no window)")
    ap.add_argument("--software", action="store_true", help="with --screenshot: use the CPU renderer (no GPU needed)")
    ap.add_argument("--host", default=DEFAULT_HOST, help=f"MQTT broker (default {DEFAULT_HOST})")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"MQTT port (default {DEFAULT_PORT})")
    ap.add_argument("--no-mqtt", action="store_true", help="don't connect to the broker (keyboard and mouse only)")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s eyes %(levelname)s %(message)s")
    args = parse_args(argv)
    try:
        window = load_window(args.side)
    except ConfigError as err:
        log.error("%s", err)       # to the log only: the screen never shows text (EYE-012)
        return 2
    theme = load_theme(args.theme)
    state = EyeState(window.position_m, theme.blink_every_s, theme.blink_ms)
    state.set_expression(args.expression, ms=0)

    if args.screenshot:
        return screenshot(args, window, theme, state)
    return run_window(args, window, theme, state)


def screenshot(args, window, theme, state) -> int:
    import pygame
    size = output_size(window, args.long_side, args.projector)
    ctx, fbo = offscreen(size, software=args.software)
    renderer = EyeRenderer(ctx, size, window, theme, args.projector, fbo, args.shape)
    frame = state.update(1.0)          # one second in: the expression has settled
    renderer.draw(frame)
    pygame.image.save(pygame.image.frombytes(renderer.read_rgba(), size, "RGBA"), args.screenshot)
    log.info("saved %s (%dx%d, %s)", args.screenshot, *size, ctx.info["GL_RENDERER"])
    return 0


def run_window(args, window, theme, state) -> int:
    import moderngl
    import pygame

    pygame.init()
    flags = pygame.OPENGL | pygame.DOUBLEBUF
    if args.fullscreen:
        flags |= pygame.FULLSCREEN
        pygame.mouse.set_visible(False)        # EYE-012
        size = (0, 0)                          # the display's own resolution
    else:
        size = output_size(window, args.long_side, args.projector)
    pygame.display.set_mode(size, flags, vsync=0 if args.no_vsync else 1)
    pygame.display.set_caption(f"Monster eye: {args.side}")
    size = pygame.display.get_surface().get_size()
    ctx = moderngl.create_context(require=310)
    log.info("%s eye, %dx%d, %s", args.side, *size, ctx.info["GL_RENDERER"])
    renderer = EyeRenderer(ctx, size, window, theme, args.projector, shape=args.shape)

    def switch_theme(name: str) -> None:
        """A theme message from the brain: new colors and blink timing, no restart (EYE-014)."""
        new = load_theme(name)                 # the default eye if it can't be read
        renderer.set_theme(new)
        state.blink_every_s, state.blink_ms = new.blink_every_s, new.blink_ms
        log.info("theme: %s", new.name)

    link = None
    if not args.no_mqtt:
        link = EyeLink(args.side, args.host, args.port)
        link.start()

    names = list(EXPRESSIONS)
    frame_times: list[float] = []
    start = last = time.perf_counter()
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                state.blink()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_i:
                state.look_idle()
            elif event.type == pygame.KEYDOWN and pygame.K_1 <= event.key <= pygame.K_6:
                state.set_expression(names[event.key - pygame.K_1], ms=300)
            elif event.type == pygame.MOUSEMOTION and not args.projector:
                scale = renderer.scale
                cx, cy = size[0] * window.eye_center[0], size[1] * window.eye_center[1]
                state.aim_sketch((event.pos[0] - cx) / scale + 150, (event.pos[1] - cy) / scale + 200)

        if link:
            for name, message, retained in link.messages():
                apply(state, name, message, retained, switch_theme)

        now = time.perf_counter()
        dt, last = now - last, now
        frame_times.append(dt)
        try:
            renderer.draw(state.update(dt))
        except Exception:                      # keep drawing whatever happens (EYE-012)
            log.exception("frame failed; carrying on")
        pygame.display.flip()
        if args.seconds and now - start > args.seconds:
            running = False

    if link:
        link.stop()                            # tells the brain "offline"
    pygame.quit()
    if args.seconds:
        print(json.dumps(timing(frame_times[30:])), flush=True)   # skip start-up frames
    return 0


def timing(times: list[float]) -> dict:
    ms = sorted(t * 1000 for t in times) or [0.0]
    return {"frames": len(times), "mean_fps": round(1000 / max(sum(ms) / len(ms), 1e-9), 1),
            "p99_frame_ms": round(ms[int(len(ms) * 0.99)], 2), "max_frame_ms": round(ms[-1], 2)}


if __name__ == "__main__":
    sys.exit(main())
