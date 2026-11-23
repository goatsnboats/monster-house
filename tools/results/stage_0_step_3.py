"""Figures and numbers for docs/results/stage-0-step-3/: the fake radar and both eyes.

    .venv/bin/python -m tools.results.stage_0_step_3            # GPU (EGL)
    .venv/bin/python -m tools.results.stage_0_step_3 --software # no GPU needed

For each scene, a pretend kid is placed on the fake radar, and the real code runs in
one process, without MQTT (the trip through Mosquitto is tests/test_step3_end_to_end.py):

    sim.radar_model (ICD-002 payloads) -> brain.radar + brain.__main__.Brain (ICD-002 -> look)
        -> eyes.state.EyeState.look_at (each eye's own angle) -> eyes.render.EyeRenderer

It writes one PNG per scene (radar view, left eye, right eye side by side) and
results.json with the messages and each eye's iris offset.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from brain.__main__ import Brain
from eyes.config import load_theme, load_window
from eyes.render import EyeRenderer, offscreen, output_size
from eyes.state import EyeState
from shared import topics
from shared.messages import eye_commands as eyes
from shared.radar_frame import load_radar_site
from sim.fake_radar import Layout, draw, eye_windows_from_site
from sim.radar_model import Kid, RadarModel

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT = REPO_ROOT / "docs" / "results" / "stage-0-step-3"

# (file name, caption, kid position in house meters)
SCENES = [
    ("01-sidewalk-left", "On the sidewalk, left of the walk", (-1.1, 5.2)),
    ("02-walk", "Halfway up the walk", (-1.1, 3.0)),
    ("03-dragged-right", "Dragged across to the right", (2.0, 3.5)),
    ("04-steps", "At the foot of the steps, close to the house", (-1.1, 2.0)),
]
EYE_LONG_SIDE = 400
RADAR_SCALE = 0.75
GAP = 24
BG = (24, 22, 30)
TEXT = (240, 240, 235)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--software", action="store_true", help="CPU renderer (no GPU)")
    args = ap.parse_args(argv)

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    pygame.init()
    font = pygame.font.Font(None, 26)
    small = pygame.font.Font(None, 22)

    site = load_radar_site()
    layout = Layout.load()
    windows = {side: load_window(side) for side in ("left", "right")}
    theme = load_theme("halloween")
    sizes = {side: output_size(w, EYE_LONG_SIDE, projector=False) for side, w in windows.items()}
    ctx, _ = offscreen(sizes["left"], software=args.software)
    renderers = {side: EyeRenderer(ctx, sizes[side], w, theme, False, ctx.simple_framebuffer(sizes[side]))
                 for side, w in windows.items()}

    OUT.joinpath("figures").mkdir(parents=True, exist_ok=True)
    results = {"renderer": ctx.info["GL_RENDERER"], "scenes": []}
    for name, caption, (kx, ky) in SCENES:
        # The pipeline: fake radar -> brain -> look message.
        model, brain, kid = RadarModel(site), Brain(site), Kid(kx, ky, "A")
        brain.radar.update(topics.RADAR_STATUS, b"online")
        radar_sent = []
        for i in range(2):
            for topic, payload in model.frame(i * 0.1, [kid]):
                brain.radar.update(topic, payload)
                radar_sent.append((topic, payload.decode()))
        (look_topic, look_payload), = brain.tick()
        look = eyes.decode("look", look_payload)

        # Each eye takes the same look point and works out its own angle.
        eye_images, offsets = {}, {}
        for side, window in windows.items():
            state = EyeState(window.position_m, theme.blink_every_s, theme.blink_ms)
            # neutral: the placeholder brain sends no expressions yet
            state.look_at((look.x, look.y, look.z))
            for _ in range(90):                     # 1.5 s at 60 fps: the glide settles
                state.heard_from_brain()            # the brain is here: no wandering, no own blinks
                frame = state.update(1 / 60)
            renderers[side].draw(frame)
            eye_images[side] = pygame.image.frombytes(renderers[side].read_rgba(), sizes[side], "RGBA")
            offsets[side] = [round(v, 1) for v in state.gaze_target]

        # The radar view.
        radar_view = pygame.Surface(layout.size)
        draw(radar_view, small, layout, site, model, [kid], "as sent", eye_windows_from_site())
        radar_view = pygame.transform.smoothscale_by(radar_view, RADAR_SCALE)

        # One image: radar | left eye | right eye.
        head = 70
        w = radar_view.get_width() + sizes["left"][0] + sizes["right"][0] + 4 * GAP
        h = head + max(radar_view.get_height(), EYE_LONG_SIDE + 30) + GAP
        sheet = pygame.Surface((w, h))
        sheet.fill(BG)
        sheet.blit(font.render(caption, True, TEXT), (GAP, 14))
        sheet.blit(small.render(f"{look_topic}  {look_payload.decode()}", True, TEXT), (GAP, 42))
        x = GAP
        sheet.blit(radar_view, (x, head))
        x += radar_view.get_width() + GAP
        for side in ("left", "right"):
            sheet.blit(small.render(f"{side} eye (street view)", True, TEXT), (x, head))
            sheet.blit(eye_images[side], (x, head + 24))
            x += sizes[side][0] + GAP
        path = OUT / "figures" / f"{name}.png"
        pygame.image.save(sheet, str(path))
        print("wrote", path.relative_to(REPO_ROOT))

        results["scenes"].append({
            "name": name, "caption": caption, "kid_house_m": [kx, ky],
            "radar_messages_first_frame": dict(radar_sent[:10]),
            "look": json.loads(look_payload),
            "iris_offset_sketch_units": offsets,
        })

    (OUT / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print("wrote", (OUT / "results.json").relative_to(REPO_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
