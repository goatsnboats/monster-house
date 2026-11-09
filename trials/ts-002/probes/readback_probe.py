"""TS-002 probe: reading pixels back from the screen, RGB vs RGBA.

Usage: readback_probe.py desktop|gles30
Clears the screen to orange (255, 128, 64) and reads the first pixel back three ways.
"""
import sys

import moderngl
import pygame

gles = sys.argv[1] == "gles30"
pygame.init()
if gles:
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_ES)
    pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
pygame.display.set_mode((64, 64), pygame.OPENGL | pygame.DOUBLEBUF)
ctx = moderngl.create_context(require=310)
ctx.clear(1.0, 0.5, 0.25, 1.0)
rgb = list(ctx.fbo.read(components=3)[:3])
rgba = list(ctx.fbo.read(components=4)[:4])
verdict = "RGB wrong" if rgb != [255, 128, 64] else "RGB right"
print(f"{sys.argv[1]:8} expected [255, 128, 64] | RGB read {rgb} | RGBA read {rgba}  -> {verdict}")
