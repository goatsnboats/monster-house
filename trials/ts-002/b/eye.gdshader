// TS-002 trial, option B: the same minimal eye as option A's eye.frag, in Godot's
// shading language (Godot turns it into GLSL ES 3.00 for the Compatibility renderer).
shader_type canvas_item;

uniform vec2  u_window = vec2(1280.0, 720.0);
uniform float u_eye_size = 0.9;
uniform bool  u_mirror = false;
uniform bool  u_rotate90 = false;
uniform vec2  u_gaze = vec2(0.0);
uniform float u_open = 1.0;
uniform float u_low = 0.0;
uniform float u_curve = 0.0;
uniform float u_pupil = 1.0;
uniform float u_spark = 0.0;

const vec3 BG     = vec3(0.043, 0.043, 0.071);
const vec3 SCLERA = vec3(0.965, 0.949, 0.902);
const vec3 IRIS   = vec3(0.478, 0.333, 0.878);
const vec3 RING   = vec3(0.231, 0.165, 0.478);
const vec3 PUPIL  = vec3(0.078, 0.059, 0.141);
const vec3 LID    = vec3(0.294, 0.184, 0.525);
const vec3 LINE   = vec3(0.102, 0.063, 0.188);

float fill(float d, float px) { return clamp(0.5 - d / px, 0.0, 1.0); }

float ellipse(vec2 p, vec2 c, vec2 r) {
    vec2 q = (p - c) / r;
    return (length(q) - 1.0) * min(r.x, r.y);
}

float star(vec2 p, vec2 c, float s) {
    vec2 q = abs(p - c) / s;
    return (sqrt(q.x) + sqrt(q.y) - 1.0) * s * 0.5;
}

void fragment() {
    vec2 w = UV * u_window;                 // pixels, y down
    vec2 size = u_window;
    if (u_rotate90) { w = vec2(w.y, u_window.x - w.x); size = u_window.yx; }
    if (u_mirror)   { w.x = size.x - w.x; }

    float scale = min(size.x / 300.0, size.y / 400.0) * u_eye_size;
    vec2 p = (w - size * 0.5) / scale + vec2(150.0, 200.0);
    float px = 1.0 / scale;

    vec3 col = BG;
    float sclera = ellipse(p, vec2(150.0, 200.0), vec2(118.0, 160.0));
    float inside = fill(sclera, px);

    vec3 eye = SCLERA;
    vec2 ic = vec2(150.0, 200.0) + u_gaze;
    float di = length(p - ic);
    eye = mix(eye, IRIS,  fill(di - 62.0, px));
    eye = mix(eye, RING,  fill(abs(di - 59.0) - 3.0, px));
    eye = mix(eye, PUPIL, fill(di - 30.0 * u_pupil, px));
    eye = mix(eye, vec3(1.0), fill(length(p - ic - vec2(-20.0, -24.0)) - 13.0, px));
    eye = mix(eye, vec3(1.0), 0.8 * fill(length(p - ic - vec2(15.0, 17.0)) - 5.0, px));
    float spark = min(star(p, ic + vec2(28.0, -32.0), 16.0), star(p, ic + vec2(-34.0, 25.0), 11.0));
    eye = mix(eye, vec3(1.0), u_spark * fill(spark, px));

    float yT = 25.0;
    float yl = 375.0 - u_low * 160.0;
    float cu = 30.0;
    float cl = 10.0 + u_curve * 45.0;
    float yu = yT + (1.0 - min(u_open, 1.2)) * (yl - yT) - (u_open > 1.0 ? (u_open - 1.0) * 60.0 : 0.0);
    float t = (p.x - 20.0) / 260.0;
    float bump = 4.0 * t * (1.0 - t);
    float slope = 4.0 * (1.0 - 2.0 * t) / 260.0;
    float upper = yu + bump * cu;
    float lower = yl - bump * cl;
    float dUp = (p.y - upper) / sqrt(1.0 + pow(slope * cu, 2.0));
    float dLo = (lower - p.y) / sqrt(1.0 + pow(slope * cl, 2.0));
    eye = mix(eye, LID,  fill(dUp, px));
    eye = mix(eye, LID,  fill(dLo, px));
    eye = mix(eye, LINE, fill(abs(dUp) - 3.5, px));
    eye = mix(eye, LINE, fill(abs(dLo) - 3.5, px));

    col = mix(col, eye, inside);
    col = mix(col, LINE, fill(abs(sclera) - 4.0, px));
    COLOR = vec4(col, 1.0);
}
