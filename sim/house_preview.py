"""House preview: the live eyes on the photo of the house, with the lips' glowing line,
to judge lopsided vs matched eyes, eye size and colors (SIM-005, SIM-006, TBD-004).

    .venv/bin/python -m sim.house_preview

It listens to the brain like a third eye (ICD-001) but never reports itself as one.
Each eye is drawn by the real eye renderer (eyes/render.py) into its own image, then
laid onto its window in the photo with a perspective warp, all on the GPU.

Mouse: drag a corner (or a lip point) to move it.
Keys: m eye mode (fills the window / oval / matched ovals / stretched) · c iris color ·
d dusk (dims the photo; the eyes are lit) · p window panes on/off · l lips on/off ·
h hide the handles ·
s save the layout to sim/house_preview.yaml · Space blink · 1-6 expressions ·
i wander · Esc quit.
"""

from __future__ import annotations

import argparse
import dataclasses
import logging
import struct
import time
from pathlib import Path

import moderngl

from eyes.config import Theme, Window, load_theme, load_window
from eyes.expressions import EXPRESSIONS
from eyes.link import EyeLink, apply
from eyes.render import GL_REQUIRE, EyeRenderer, offscreen, output_size
from eyes.state import EyeState
from shared.mqtt_client import DEFAULT_HOST, DEFAULT_PORT
from sim.house_layout import LAYOUT_FILE, SIDES, HouseLayout, LayoutError, load_layout, photo_to_eye, save_layout

log = logging.getLogger("house_preview")

EYE_LONG_SIDE_PX = 360          # each eye's own image; the photo windows are smaller
HANDLE_PX = 10                  # handle radius on screen
MAX_LIP_POINTS = 8              # per lip
DUSK = (1.0, 0.55, 0.3)         # photo brightness steps for d
MODES = ("window", "oval", "matched", "stretch")
MODE_TEXT = {
    "window": "each eye fills its window (lopsided)",
    "oval": "ovals, as big as each window (lopsided)",
    "matched": "ovals, both the small window's size (matched)",
    "stretch": "ovals stretched to each window",
}

VERT_CLIP = """#version 300 es
in vec2 pos;
out vec2 v_photo;
uniform vec2 u_photo;           // photo size, px
void main() {
    v_photo = pos;
    gl_Position = vec4(pos.x / u_photo.x * 2.0 - 1.0, 1.0 - pos.y / u_photo.y * 2.0, 0.0, 1.0);
}
"""

FRAG_PHOTO = """#version 300 es
precision mediump float;
in vec2 v_photo;
out vec4 color;
uniform sampler2D u_tex;
uniform vec2 u_photo;
uniform float u_dim;
void main() { color = vec4(texture(u_tex, v_photo / u_photo).rgb * u_dim, 1.0); }
"""

FRAG_EYE = """#version 300 es
precision highp float;
in vec2 v_photo;
out vec4 color;
uniform sampler2D u_tex;
uniform mat3 u_to_eye;          // photo px -> eye image 0..1 (top-left origin)
uniform vec2 u_vbars[4];        // vertical pane bars: x, width (fractions of the glass)
uniform vec2 u_hbars[4];        // horizontal pane bars: y, height
uniform int u_nv;
uniform int u_nh;
uniform vec3 u_pane_color;
void main() {
    vec3 p = u_to_eye * vec3(v_photo, 1.0);
    vec2 uv = p.xy / p.z;
    if (any(lessThan(uv, vec2(0.0))) || any(greaterThan(uv, vec2(1.0)))) discard;
    vec3 rgb = texture(u_tex, vec2(uv.x, 1.0 - uv.y)).rgb;           // GL images start at the bottom
    for (int i = 0; i < 4; i++) {
        if (i < u_nv && abs(uv.x - u_vbars[i].x) < u_vbars[i].y * 0.5) rgb = u_pane_color;
        if (i < u_nh && abs(uv.y - u_hbars[i].x) < u_hbars[i].y * 0.5) rgb = u_pane_color;
    }
    color = vec4(rgb, 1.0);
}
"""

FRAG_OVERLAY = """#version 300 es
precision highp float;
in vec2 v_photo;
out vec4 color;
uniform vec2 u_lips[16];        // two lips, 8 points each (photo px)
uniform int u_lip_n[2];
uniform vec3 u_lip_color;
uniform float u_lips_on;
uniform vec2 u_handles[32];
uniform int u_handle_n;
uniform float u_px;             // photo px per screen px
float seg(vec2 p, vec2 a, vec2 b) {
    vec2 ab = b - a;
    float t = clamp(dot(p - a, ab) / max(dot(ab, ab), 1e-6), 0.0, 1.0);
    return length(p - a - ab * t);
}
void main() {
    float d = 1e6;
    for (int l = 0; l < 2; l++)
        for (int i = 0; i < 7; i++)
            if (i + 1 < u_lip_n[l]) d = min(d, seg(v_photo, u_lips[l * 8 + i], u_lips[l * 8 + i + 1]));
    float glow = u_lips_on * (smoothstep(7.0, 3.0, d) + 0.55 * exp(-d * d / (2.0 * 28.0 * 28.0)));
    vec3 rgb = u_lip_color * glow;
    float a = 0.0;
    for (int i = 0; i < 32; i++) {
        if (i >= u_handle_n) break;
        float r = length(v_photo - u_handles[i]) / u_px;
        float ring = smoothstep(2.5, 1.0, abs(r - 10.0));
        float dark = smoothstep(4.5, 3.0, abs(r - 10.0));
        rgb = mix(rgb, vec3(0.0), dark * (1.0 - ring));
        rgb = mix(rgb, vec3(1.0), ring);
        a = max(a, dark);
    }
    color = vec4(rgb, a);         // premultiplied: glow adds, handles cover
}
"""


def _hex(c: str) -> tuple[float, float, float]:
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))


def eye_window(window: Window, mode: str, small: Window) -> tuple[Window, str]:
    """The window settings and shape for a preview mode."""
    if mode == "window":
        return window, "square"
    if mode in ("oval", "stretch"):
        return window, mode
    # matched: an oval as big as the small window's, in meters, in every window
    unit = lambda w: min(w.window_m[0] / 300, w.window_m[1] / 400)   # noqa: E731  (m per sketch unit)
    size = small.eye_size * unit(small) / unit(window)
    return dataclasses.replace(window, eye_size=size), "oval"


class Preview:
    """Everything drawn, without a window of its own (so screenshots and tests can use it)."""

    def __init__(self, ctx: moderngl.Context, target: moderngl.Framebuffer, view: tuple[int, int],
                 layout: HouseLayout, windows: dict[str, Window], theme: Theme) -> None:
        import pygame                                   # only to read the photo
        self.ctx, self.target, self.view = ctx, target, view
        self.layout, self.windows, self.theme = layout, windows, theme
        img = pygame.image.load(str(layout.photo))
        self.photo_size = img.get_size()
        self.px = self.photo_size[1] / view[1]          # photo px per screen px
        self.photo_tex = ctx.texture(self.photo_size, 3, pygame.image.tobytes(img, "RGB"))
        self.photo_tex.build_mipmaps()
        self.photo_tex.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)

        self.p_photo = ctx.program(vertex_shader=VERT_CLIP, fragment_shader=FRAG_PHOTO)
        self.p_eye = ctx.program(vertex_shader=VERT_CLIP, fragment_shader=FRAG_EYE)
        self.p_over = ctx.program(vertex_shader=VERT_CLIP, fragment_shader=FRAG_OVERLAY)
        for p in (self.p_photo, self.p_eye, self.p_over):
            p["u_photo"].value = self.photo_size
        w, h = self.photo_size
        self.full = ctx.buffer(struct.pack("8f", 0, 0, w, 0, 0, h, w, h))
        self.vao_photo = ctx.vertex_array(self.p_photo, [(self.full, "2f", "pos")])
        self.vao_over = ctx.vertex_array(self.p_over, [(self.full, "2f", "pos")])
        self.quads = {s: ctx.buffer(reserve=32) for s in SIDES}
        self.vao_eye = {s: ctx.vertex_array(self.p_eye, [(self.quads[s], "2f", "pos")]) for s in SIDES}

        self.mode = "window"
        self.iris = 0
        self.dusk = 0
        self.lips_on = True
        self.panes_on = True
        self.handles_on = True
        self.eyes: dict[str, EyeRenderer] = {}
        self.eye_fbo: dict[str, moderngl.Framebuffer] = {}
        self.set_mode(self.mode)
        self.corners_changed()

    # ── Settings ──────────────────────────────────────────────────────────────────

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        small = min(self.windows.values(), key=lambda w: w.window_m[0] * w.window_m[1])
        for side in SIDES:
            window, shape = eye_window(self.windows[side], mode, small)
            size = output_size(window, EYE_LONG_SIDE_PX, projector=False)
            tex = self.ctx.texture(size, 4)
            tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
            self.eye_fbo[side] = self.ctx.framebuffer(color_attachments=[tex])
            self.eyes[side] = EyeRenderer(self.ctx, size, window, self.theme, projector=False,
                                          target=self.eye_fbo[side], shape=shape)
        self.set_iris(self.iris)

    def set_iris(self, i: int) -> None:
        colors = self.layout.iris_colors
        self.iris = i % len(colors) if colors else 0
        theme = dataclasses.replace(self.theme, iris_color=_hex(colors[self.iris])) if colors else self.theme
        for r in self.eyes.values():
            r.set_theme(theme)

    def corners_changed(self) -> None:
        for side in SIDES:
            tl, tr, br, bl = self.layout.windows[side]
            self.quads[side].write(struct.pack("8f", *tl, *tr, *bl, *br))   # a triangle strip

    def handles(self) -> list[tuple[str, str, int]]:
        """Every draggable point: (group, name, index)."""
        out = [("windows", s, i) for s in SIDES for i in range(4)]
        out += [("lips", name, i) for name, pts in self.layout.lips.items() for i in range(len(pts))]
        return out

    def point(self, h: tuple[str, str, int]) -> tuple[float, float]:
        group, name, i = h
        return getattr(self.layout, group)[name][i]

    def move(self, h: tuple[str, str, int], p: tuple[float, float]) -> None:
        group, name, i = h
        getattr(self.layout, group)[name][i] = p
        if group == "windows":
            self.corners_changed()

    def to_photo(self, screen: tuple[float, float]) -> tuple[float, float]:
        return (screen[0] * self.px, screen[1] * self.px)

    def nearest(self, screen: tuple[float, float]) -> tuple[str, str, int] | None:
        x, y = self.to_photo(screen)
        best = min(self.handles(), key=lambda h: (self.point(h)[0] - x) ** 2 + (self.point(h)[1] - y) ** 2)
        bx, by = self.point(best)
        return best if ((bx - x) ** 2 + (by - y) ** 2) ** 0.5 <= 2 * HANDLE_PX * self.px else None

    # ── Drawing ───────────────────────────────────────────────────────────────────

    def draw(self, frames: dict) -> None:
        for side in SIDES:
            self.eyes[side].draw(frames[side])
        self.target.use()
        self.ctx.viewport = (0, 0, *self.view)
        self.ctx.disable(moderngl.BLEND)
        self.p_photo["u_dim"].value = DUSK[self.dusk]
        self.photo_tex.use(0)
        self.p_photo["u_tex"].value = 0
        self.vao_photo.render(moderngl.TRIANGLE_STRIP)
        for side in SIDES:
            try:
                m = photo_to_eye(self.layout.windows[side])
            except ValueError:
                continue                                    # a corner dragged into a twist
            self.eye_fbo[side].color_attachments[0].use(0)
            self.p_eye["u_tex"].value = 0
            self.p_eye["u_to_eye"].value = tuple(m[r][c] for c in range(3) for r in range(3))  # column-major
            bars = self.layout.panes.get(side, {}) if self.panes_on else {}
            v, h = bars.get("v", [])[:4], bars.get("h", [])[:4]
            self.p_eye["u_vbars"].value = v + [(0.0, 0.0)] * (4 - len(v))
            self.p_eye["u_hbars"].value = h + [(0.0, 0.0)] * (4 - len(h))
            self.p_eye["u_nv"].value, self.p_eye["u_nh"].value = len(v), len(h)
            self.p_eye["u_pane_color"].value = _hex(self.layout.pane_color)
            self.vao_eye[side].render(moderngl.TRIANGLE_STRIP)
        self._overlay()

    def _overlay(self) -> None:
        lips = list(self.layout.lips.values())[:2]
        flat, counts = [], []
        for pts in lips + [[]] * (2 - len(lips)):
            pts = pts[:MAX_LIP_POINTS]
            counts.append(len(pts))
            flat += pts + [(0.0, 0.0)] * (MAX_LIP_POINTS - len(pts))
        handles = [self.point(h) for h in self.handles()][:32] if self.handles_on else []
        p = self.p_over
        p["u_lips"].value = flat
        p["u_lip_n"].value = counts
        p["u_lip_color"].value = _hex(self.layout.lip_color)
        p["u_lips_on"].value = 1.0 if self.lips_on else 0.0
        p["u_handles"].value = handles + [(0.0, 0.0)] * (32 - len(handles))
        p["u_handle_n"].value = len(handles)
        p["u_px"].value = self.px
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.ONE, moderngl.ONE_MINUS_SRC_ALPHA
        self.vao_over.render(moderngl.TRIANGLE_STRIP)
        self.ctx.disable(moderngl.BLEND)

    def caption(self) -> str:
        return (f"House preview: {MODE_TEXT[self.mode]} · iris {self.layout.iris_colors[self.iris] if self.layout.iris_colors else ''}"
                f" · dusk {DUSK[self.dusk]:.2f}")


def new_states(windows: dict[str, Window], theme: Theme) -> dict[str, EyeState]:
    """One state per eye, on the same clock so they wander and blink together."""
    return {s: EyeState(windows[s].position_m, theme.blink_every_s, theme.blink_ms, clock_start=time.time())
            for s in SIDES}


def view_size(photo: tuple[int, int], height: int) -> tuple[int, int]:
    return round(photo[0] * height / photo[1]), height


def parse_args(argv=None):
    p = argparse.ArgumentParser(prog="python -m sim.house_preview", description=__doc__.split("\n\n")[0])
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--no-mqtt", action="store_true", help="don't listen to the brain; the eyes wander")
    p.add_argument("--height", type=int, default=1000, help="window height in pixels")
    p.add_argument("--layout", type=Path, default=LAYOUT_FILE)
    p.add_argument("--theme", default="halloween")
    p.add_argument("--screenshot", type=Path, help="draw one frame to a PNG, then quit (no window)")
    p.add_argument("--mode", choices=MODES, default="window")
    p.add_argument("--software", action="store_true", help="with --screenshot: no GPU needed")
    return p.parse_args(argv)


def render_png(path: Path, layout: HouseLayout, windows, theme, height: int, mode: str = "window",
               expression: str | None = None, software: bool = False, handles: bool = False,
               iris: int = 0, dusk: int = 0, settle_s: float = 1.0,
               look: tuple[float, float, float] = (0.8, 4.0, 1.0), panes: bool = True) -> None:
    """One frame drawn offscreen and saved as a PNG (for docs and tests). The eyes look at
    `look` (house m; default a kid on the walk, right of center)."""
    import pygame
    img = pygame.image.load(str(layout.photo))
    view = view_size(img.get_size(), height)
    ctx, fbo = offscreen(view, software=software)
    preview = Preview(ctx, fbo, view, layout, windows, theme)
    preview.set_mode(mode)
    preview.set_iris(iris)
    preview.dusk, preview.handles_on, preview.panes_on = dusk, handles, panes
    states = {s: EyeState(windows[s].position_m, (1e6, 1e6), theme.blink_ms) for s in SIDES}
    for st in states.values():
        st.look_at(look)
        if expression:
            st.set_expression(expression, ms=0)
        st.heard_from_brain()
    frames = {}
    for _ in range(int(settle_s * 60)):
        frames = {s: states[s].update(1 / 60) for s in SIDES}
        for st in states.values():
            st.heard_from_brain()
    preview.draw(frames)
    data = fbo.read(components=4)
    row = view[0] * 4
    flipped = b"".join(data[y * row:(y + 1) * row] for y in reversed(range(view[1])))
    pygame.image.save(pygame.image.frombuffer(flipped, view, "RGBA"), str(path))


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    args = parse_args(argv)
    try:
        layout = load_layout(args.layout)
    except LayoutError as err:
        log.error("%s", err)
        return 2
    windows = {s: load_window(s) for s in SIDES}
    theme = load_theme(args.theme)
    if args.screenshot:
        render_png(args.screenshot, layout, windows, theme, args.height, args.mode, software=args.software,
                   handles=True)
        return 0
    return run_window(args, layout, windows, theme)


def run_window(args, layout: HouseLayout, windows, theme) -> int:
    import pygame

    pygame.init()
    img_size = pygame.image.load(str(layout.photo)).get_size()
    view = view_size(img_size, args.height)
    pygame.display.set_mode(view, pygame.OPENGL | pygame.DOUBLEBUF, vsync=1)
    ctx = moderngl.create_context(require=GL_REQUIRE)
    preview = Preview(ctx, ctx.screen, view, layout, windows, theme)
    preview.set_mode(args.mode)
    pygame.display.set_caption(preview.caption())
    states = new_states(windows, theme)

    def switch_theme(name: str) -> None:
        nonlocal theme
        theme = load_theme(name)
        preview.theme = theme
        preview.set_iris(preview.iris)

    link = None
    if not args.no_mqtt:
        link = EyeLink(None, args.host, args.port, client_name="house-preview")
        link.start()

    names = list(EXPRESSIONS)
    dragging = None
    last = time.perf_counter()
    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE):
                running = False
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and preview.handles_on:
                dragging = preview.nearest(e.pos)
            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                dragging = None
            elif e.type == pygame.MOUSEMOTION and dragging:
                preview.move(dragging, preview.to_photo(e.pos))
            elif e.type == pygame.KEYDOWN:
                k = e.key
                if k == pygame.K_m:
                    preview.set_mode(MODES[(MODES.index(preview.mode) + 1) % len(MODES)])
                elif k == pygame.K_c:
                    preview.set_iris(preview.iris + 1)
                elif k == pygame.K_d:
                    preview.dusk = (preview.dusk + 1) % len(DUSK)
                elif k == pygame.K_l:
                    preview.lips_on = not preview.lips_on
                elif k == pygame.K_p:
                    preview.panes_on = not preview.panes_on
                elif k == pygame.K_h:
                    preview.handles_on = not preview.handles_on
                elif k == pygame.K_s:
                    save_layout(preview.layout, args.layout)
                    log.info("saved the layout to %s", args.layout)
                elif k == pygame.K_SPACE:
                    for st in states.values():
                        st.blink()
                elif k == pygame.K_i:
                    for st in states.values():
                        st.look_idle()
                elif pygame.K_1 <= k <= pygame.K_6:
                    for st in states.values():
                        st.set_expression(names[k - pygame.K_1], ms=300)
                pygame.display.set_caption(preview.caption())

        if link:
            for name, message, retained in link.messages():
                for st in states.values():
                    apply(st, name, message, retained, switch_theme)

        now = time.perf_counter()
        dt, last = now - last, now
        try:
            preview.draw({s: states[s].update(dt) for s in SIDES})
        except Exception:                                   # keep drawing whatever happens
            log.exception("frame failed; carrying on")
        pygame.display.flip()

    if link:
        link.stop()
    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
