"""TS-002 probe: can moderngl run at the Raspberry Pi 5's OpenGL level?

Usage: gl_probe.py MODE REQUIRE
  MODE     desktop  - the machine's normal OpenGL (set MESA_GL_VERSION_OVERRIDE=3.1 to cap it like the Pi)
           gles30   - an OpenGL ES 3.0 context (set SDL_VIDEO_X11_FORCE_EGL=1 under X11)
  REQUIRE  moderngl's minimum version code, e.g. 310 for OpenGL 3.1
Prints one line: OK or FAIL, the context version, and whether a GLSL ES 3.00 shader compiled.
"""
import sys

import moderngl
import pygame

mode, require = sys.argv[1], int(sys.argv[2])
pygame.init()
if mode == "gles30":
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_ES)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 0)
pygame.display.set_mode((320, 200), pygame.OPENGL | pygame.DOUBLEBUF)
try:
    ctx = moderngl.create_context(require=require)
    ctx.program(
        vertex_shader="#version 300 es\nin vec2 p; void main(){ gl_Position = vec4(p, 0.0, 1.0); }",
        fragment_shader="#version 300 es\nprecision mediump float; out vec4 c; void main(){ c = vec4(1.0); }",
    )
    print(f"OK    mode={mode:8} require={require}  context: {ctx.info['GL_VERSION']}  | GLSL ES 3.00 shader compiled")
except Exception as e:  # noqa: BLE001 - a probe reports any failure
    print(f"FAIL  mode={mode:8} require={require}  {type(e).__name__}: {str(e).splitlines()[0][:100]}")
