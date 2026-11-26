"""Drawing one eye with moderngl (ADR 0002): one full-window quad and one fragment shader.

All per-pixel work happens in the shader on the GPU (EYE-010); each frame the CPU only
sets a dozen numbers. Works in a pygame window or offscreen (tests and screenshots).
"""

from __future__ import annotations

import os
import struct
from pathlib import Path

import moderngl

from eyes.config import SHAPES, Theme, Window
from eyes.state import Frame

SHADER_DIR = Path(__file__).resolve().parent / "shaders"
VERTEX_SHADER = "#version 300 es\nin vec2 pos;\nvoid main() { gl_Position = vec4(pos, 0.0, 1.0); }\n"
GL_REQUIRE = 310   # the Pi 5 offers OpenGL 3.1 / GLES 3.1 (ADR 0002)


def output_size(window: Window, long_side_px: int, projector: bool) -> tuple[int, int]:
    """Pixel size for an eye's output, shaped like its real window.

    Street view (projector=False): the window as people see it from the street.
    Projector view: turned a quarter turn when the projector lies on its side.
    """
    w_m, h_m = window.window_m
    scale = long_side_px / max(w_m, h_m)
    w, h = round(w_m * scale), round(h_m * scale)
    if projector and window.rotate_deg == 90:
        w, h = h, w
    return w, h


def layout(size: tuple[int, int], eye_size: float, shape: str) -> tuple[float, tuple[float, float], bool]:
    """How the eye fills its output: (pixels per sketch unit, stretch, fill a rectangle).

    square   the white fills the whole window; the window frame is the eye's edge
             (eye_size is not used); the iris is sized to the white, not the whole sketch
    oval     the sketch's oval (3 wide x 4 tall), as big as fits (eye_size of the window)
    stretch  an oval stretched to the window's shape (eye_size of each side)
    The size here is the window as seen from the street (before any rotation).
    """
    sx, sy = size[0] / 300, size[1] / 400
    scale = min(sx, sy)
    if shape == "oval":
        return scale * eye_size, (1.0, 1.0), False
    if shape == "stretch":
        return scale * eye_size, (sx / scale, sy / scale), False
    if shape == "square":
        # The white is 236 x 320 sketch units. Size the round things (iris, pupil, lines) as
        # if that white were scaled up to just fit the window (owner, 2026-11-26: a bigger
        # iris), then stretch the white to cover the whole window.
        scale = min(size[0] / 236, size[1] / 320)
        return scale, (size[0] / (236 * scale), size[1] / (320 * scale)), True
    raise ValueError(f"eye shape must be one of {SHAPES}, not {shape!r}")


class EyeRenderer:
    def __init__(self, ctx: moderngl.Context, size: tuple[int, int], window: Window, theme: Theme,
                 projector: bool, target: moderngl.Framebuffer | None = None, shape: str | None = None) -> None:
        """projector=False draws the street view (no rotation or mirroring).
        target: where to draw; the window (ctx.screen) unless given."""
        self.ctx = ctx
        self.target = target or ctx.screen
        self.prog = ctx.program(vertex_shader=VERTEX_SHADER,
                                fragment_shader=(SHADER_DIR / "eye.frag").read_text())
        quad = ctx.buffer(struct.pack("8f", -1, -1, 1, -1, -1, 1, 1, 1))  # covers the whole output
        self.vao = ctx.vertex_array(self.prog, [(quad, "2f", "pos")])
        self.size = size
        self.prog["u_window"].value = size
        self.prog["u_rotate90"].value = projector and window.rotate_deg == 90
        self.prog["u_mirror"].value = projector and window.mirror
        self.prog["u_eye_center"].value = window.eye_center
        street = size[::-1] if projector and window.rotate_deg == 90 else size
        self.scale, stretch, fill = layout(street, window.eye_size, shape or window.eye_shape)
        self.prog["u_scale"].value = self.scale
        self.prog["u_stretch"].value = stretch
        self.prog["u_fill"].value = fill
        self.prog["u_brightness"].value = window.brightness
        self.set_theme(theme)

    def set_theme(self, theme: Theme) -> None:
        """Switch colors without restarting (EYE-014)."""
        self.prog["u_iris"].value = theme.iris_color
        self.prog["u_sclera"].value = theme.sclera_color

    def draw(self, frame: Frame) -> None:
        e = frame.expression
        self.prog["u_gaze"].value = frame.gaze
        self.prog["u_open"].value = e.open
        self.prog["u_low"].value = e.low
        self.prog["u_curve"].value = e.curve
        self.prog["u_pupil"].value = e.pupil
        self.prog["u_spark"].value = e.spark
        self.target.use()
        self.target.clear()
        self.vao.render(moderngl.TRIANGLE_STRIP)

    def read_rgba(self) -> bytes:
        """The pixels just drawn, top row first, as RGBA bytes (for screenshots and tests)."""
        w, h = self.size
        data = self.target.read(components=4)            # GLES only guarantees RGBA read-back
        row = w * 4
        return b"".join(data[y * row:(y + 1) * row] for y in reversed(range(h)))   # GL starts at the bottom


def offscreen(size: tuple[int, int], software: bool = False) -> tuple[moderngl.Context, moderngl.Framebuffer]:
    """A GL context and an offscreen image of `size` to draw into, with no window (EGL).

    software=True uses Mesa's CPU renderer (llvmpipe): no GPU access needed, so it works
    in tests and over SSH, but it says nothing about speed.
    """
    if software:
        os.environ["EGL_PLATFORM"] = "surfaceless"
        os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
    ctx = moderngl.create_standalone_context(require=GL_REQUIRE, backend="egl")
    return ctx, ctx.simple_framebuffer(size)
