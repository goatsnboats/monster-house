"""Make the figures for the TS-002 results report.

Usage (trial venv with playwright, pygments; after run_trials.py and score.py):

    trials/ts-002/.venv/bin/python trials/ts-002/make_figures.py RUN_DIR SCORES_JSON FIG_DIR [VALIDATOR_JS]

RUN_DIR is run_trials.py's output folder. VALIDATOR_JS is the dataviz skill's
validate_palette.js; if given, it runs inside each chart page and its report is saved
as FIG_DIR/palette-validator.md.

Charts follow the dataviz reference palette (light mode, surface #fcfcfb): option A is
categorical slot 1 (blue), option B slot 2 (orange), always. They are static PNGs for a
Markdown report, so they have no hover layer; every value is also in the report's tables.
"""

from __future__ import annotations

import base64
import difflib
import html
import json
import statistics
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import GLShaderLexer

HERE = Path(__file__).resolve().parent
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#8a8984", "#e1e0d9", "#fcfcfb"
COL = {"A": "#2a78d6", "B": "#eb6834"}
LABEL = {"A": "A  Python + moderngl", "B": "B  Godot 4.7.2"}
STATES = ["neutral", "happy", "sparkle", "sleepy", "happy-rot-mirror"]
STATE_LABEL = {"neutral": "neutral", "happy": "happy", "sparkle": "sparkle", "sleepy": "sleepy",
               "happy-rot-mirror": "happy, rotated 90° + mirrored"}

BASE_CSS = f"""
body {{ margin:0; background:{SURF}; color:{INK}; font: 15px/1.45 system-ui, -apple-system, 'Segoe UI', sans-serif; }}
.fig {{ display:inline-block; padding:20px 24px; background:{SURF}; }}
h1 {{ font-size:17px; margin:0 0 4px; }} .sub {{ color:{INK2}; font-size:13px; margin:0 0 14px; max-width:1100px; }}
pre, code {{ font-family: 'DejaVu Sans Mono', 'Ubuntu Mono', monospace; font-size:12.5px; }}
.legend {{ font-size:13px; color:{INK}; margin:0 0 8px; }}
.lg {{ display:inline-flex; align-items:center; gap:6px; margin-right:18px; }}
svg text {{ font-family: system-ui, -apple-system, 'Segoe UI', sans-serif; }}
"""


def page(body: str, css: str = "", palette: str | None = None) -> str:
    attrs = f" data-palette='{palette}' data-mode='light'" if palette else ""
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{BASE_CSS}{css}</style></head><body{attrs}>{body}</body></html>"


def shoot(pw, html_text: str, out: Path, width: int = 1300, validator: str | None = None) -> list[str]:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": width, "height": 900}, device_scale_factor=2)
    logs: list[str] = []
    pg.on("console", lambda m: logs.append(m.text))
    pg.set_content(html_text, wait_until="load")
    if validator:
        pg.evaluate("console.table = (rows) => console.log(JSON.stringify(rows))")
        pg.add_script_tag(content=validator, type="module")
    pg.wait_for_timeout(600)
    pg.locator(".fig").first.screenshot(path=str(out))
    b.close()
    return logs


def img64(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def legend(keys=("A", "B"), shapes=True) -> str:
    out = []
    for k in keys:
        mark = (f"<svg width='14' height='14'><circle cx='7' cy='7' r='5' fill='{COL[k]}'/></svg>" if k == "A" or not shapes
                else f"<svg width='14' height='14'><rect x='2' y='2' width='10' height='10' fill='{COL[k]}'/></svg>")
        out.append(f"<span class='lg'>{mark}{html.escape(LABEL[k])}</span>")
    return f"<div class='legend'>{''.join(out)}</div>"


# ------------------------------------------------------------------ 01 expressions
def expressions_fig(pw, shots: Path, out: Path):
    cells = "".join(f"<th>{html.escape(STATE_LABEL[s])}</th>" for s in STATES)
    rows = ""
    for opt in ("A", "B"):
        imgs = "".join(f"<td><img src='{img64(shots / f'{opt.lower()}-{s}.png')}' width='224'></td>" for s in STATES)
        rows += f"<tr><th class='r'>{html.escape(LABEL[opt])}</th>{imgs}</tr>"
    body = (f"<div class='fig'><h1>The same minimal eye, built both ways</h1>"
            f"<p class='sub'>Screenshots at 1280×720 on OpenGL ES. Both use the same shader math. "
            f"The pupils differ only because each eye wanders randomly. The last column shows the projector-on-its-side rotation plus "
            f"rear-projection mirroring.</p><table><tr><th></th>{cells}</tr>{rows}</table></div>")
    css = (f"table {{ border-collapse:separate; border-spacing:6px; }} th {{ font-size:13px; color:{INK2}; font-weight:600; }}"
           f" th.r {{ text-align:right; width:150px; color:{INK}; }} img {{ display:block; border-radius:4px; }}")
    shoot(pw, page(body, css), out)


# ------------------------------------------------------------------ 02 shader side by side
def shader_fig(pw, out: Path):
    """Both drawing functions in full; code lines that differ are highlighted (comments and blanks ignored)."""
    def body_lines(path: Path, head: str) -> list[str]:
        src = path.read_text()
        return (head + src.split(head, 1)[1]).splitlines()

    a = body_lines(HERE / "a" / "eye.frag", "void main() {")
    b = body_lines(HERE / "b" / "eye.gdshader", "void fragment() {")

    def code_only(lines: list[str]) -> tuple[list[str], list[int]]:
        keep, idx = [], []
        for i, ln in enumerate(lines):
            c = ln.split("//")[0].strip()
            if c:
                keep.append(c)
                idx.append(i)
        return keep, idx

    ca, ia = code_only(a)
    cb, ib = code_only(b)
    sm = difflib.SequenceMatcher(None, ca, cb, autojunk=False)
    diff_a, diff_b, same = set(), set(), 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            same += i2 - i1
        else:
            diff_a.update(ia[k] for k in range(i1, i2))
            diff_b.update(ib[k] for k in range(j1, j2))

    def pane(title: str, lines: list[str], marks: set[int]) -> str:
        rows = []
        for i, ln in enumerate(lines):
            code = highlight(ln, GLShaderLexer(), HtmlFormatter(nowrap=True)).rstrip() or "&nbsp;"
            rows.append(f"<div{' class=hl' if i in marks else ''}>{code}</div>")
        return f"<div class='card'><h2>{title}</h2><pre>{''.join(rows)}</pre></div>"

    body = (f"<div class='fig'><h1>The drawing code is the same in both</h1>"
            f"<p class='sub'>Option A's GLSL ES 3.00 shader beside Option B's Godot shader: the whole drawing function of each. "
            f"Highlighted lines differ (comments and blank lines ignored): <b>{same} of {len(ca)} code lines in A are identical in B</b>. "
            f"The differences are the function's name, where the pixel position comes from, and the name of the output.</p>"
            f"<div class='row'>{pane('A — trials/ts-002/a/eye.frag (GLSL ES 3.00)', a, diff_a)}"
            f"{pane('B — trials/ts-002/b/eye.gdshader (Godot shading language)', b, diff_b)}</div></div>")
    css = (HtmlFormatter(style="friendly").get_style_defs(".card pre") +
           f".row {{ display:flex; gap:14px; }} .card {{ border:1px solid {GRID}; border-radius:8px; background:#fff; width:780px; overflow:hidden; }}"
           f".card h2 {{ font-size:13.5px; margin:0; padding:8px 12px; border-bottom:1px solid {GRID}; background:#f4f3ef; }}"
           f".card pre {{ margin:0; padding:8px 0; font-size:10.5px; line-height:1.45; }} .card pre div {{ padding:0 12px; white-space:pre; }}"
           f".hl {{ background:#fff3c4; }}")
    shoot(pw, page(body, css), out, width=1640)


# ------------------------------------------------------------------ charts (SVG)
def hbar(x0: float, y: float, x1: float, h: float, color: str) -> str:
    r = min(4, (x1 - x0) / 2)
    return (f"<path d='M{x0},{y} H{x1 - r} Q{x1},{y} {x1},{y + r} V{y + h - r} Q{x1},{y + h} {x1 - r},{y + h} H{x0} Z' "
            f"fill='{color}'/>")


def bar_panel(title: str, unit: str, values: dict[str, float], vmax: float, ticks: list[float], fmt, note: str = "") -> str:
    w, left, right, top = 380, 40, 70, 34
    plot = w - left - right
    sx = lambda v: left + plot * v / vmax  # noqa: E731
    svg = [f"<svg width='{w}' height='150'>"]
    for t in ticks:
        svg.append(f"<line x1='{sx(t)}' x2='{sx(t)}' y1='{top - 6}' y2='{top + 76}' stroke='{GRID}' stroke-width='1'/>"
                   f"<text x='{sx(t)}' y='{top + 92}' font-size='11' fill='{MUTED}' text-anchor='middle'>{fmt(t)}</text>")
    for i, opt in enumerate(("A", "B")):
        y = top + i * 38
        v = values[opt]
        svg.append(f"<text x='{left - 10}' y='{y + 15}' font-size='13' fill='{INK}' text-anchor='end' font-weight='600'>{opt}</text>")
        svg.append(hbar(left, y, sx(v), 22, COL[opt]))
        svg.append(f"<text x='{sx(v) + 6}' y='{y + 15}' font-size='13' fill='{INK}'>{fmt(v)}{unit}</text>")
    svg.append(f"<line x1='{left}' x2='{left}' y1='{top - 6}' y2='{top + 76}' stroke='{MUTED}' stroke-width='1'/></svg>")
    return f"<div class='panel'><h2>{title}</h2>{''.join(svg)}<p class='note'>{note}</p></div>"


def resources_fig(pw, res: dict, out: Path, validator: str | None) -> list[str]:
    capped = res["capped_60fps"]
    mean = lambda opt, key: statistics.mean(r[key] for r in capped[opt] if key in r)  # noqa: E731
    unc = {o: statistics.mean(r["summary"]["mean_frame_ms"] for r in res["uncapped"][o] if r["summary"]) for o in ("A", "B")}
    cpu = {o: mean(o, "cpu_pct") for o in ("A", "B")}
    mem = {o: mean(o, "peak_rss_mb") for o in ("A", "B")}
    p1 = bar_panel("CPU at 60 fps", " %", cpu, 8, [0, 2, 4, 6, 8], lambda v: f"{v:.1f}" if v % 1 else f"{v:.0f}",
                   "% of one CPU core, mean of runs (lower is better)")
    p2 = bar_panel("Memory at 60 fps", " MB", mem, 250, [0, 100, 200], lambda v: f"{v:.0f}",
                   "Peak resident memory; includes the desktop's Intel driver")
    p3 = bar_panel("Cost per frame, uncapped", " ms", unc, 4, [0, 1, 2, 3, 4], lambda v: f"{v:.2f}" if v < 1 else f"{v:.1f}",
                   "Mean time per frame with no cap; the 60 fps budget is 16.7 ms")
    body = (f"<div class='fig'><h1>What each option costs while drawing the eye</h1>"
            f"<p class='sub'>1280×720, OpenGL ES, on the Ubuntu desktop (Intel Arrow Lake graphics). Three separate scales; "
            f"lower is better in every panel.</p>{legend(shapes=False)}<div class='row'>{p1}{p2}{p3}</div></div>")
    css = (f".row {{ display:flex; gap:20px; }} .panel h2 {{ font-size:14px; margin:6px 0 0 40px; }}"
           f" .note {{ font-size:12px; color:{INK2}; margin:0 0 0 40px; max-width:300px; }}")
    return shoot(pw, page(body, css, palette=f"{COL['A']},{COL['B']}"), out, validator=validator)


def frames_fig(pw, run_dir: Path, out: Path, validator: str | None) -> list[str]:
    panels = []
    for opt in ("A", "B"):
        ms = [float(x) for x in (run_dir / "frames" / f"{opt.lower()}-capped-run1.txt").read_text().split()]
        ms = ms[30:]                          # skip start-up frames, as the summary does
        t, xs = 0.0, []
        for v in ms:
            t += v / 1000
            xs.append(t)
        w, h, left, top, plot_h = 1100, 170, 50, 12, 130
        tmax, vmax = 27, 30
        sx = lambda x: left + (w - left - 20) * x / tmax  # noqa: E731
        sy = lambda v: top + plot_h * (1 - min(v, vmax) / vmax)  # noqa: E731
        svg = [f"<svg width='{w}' height='{h + 18}'>"]
        for v in (0, 10, 20, 30):
            svg.append(f"<line x1='{left}' x2='{w - 20}' y1='{sy(v)}' y2='{sy(v)}' stroke='{GRID}'/>"
                       f"<text x='{left - 8}' y='{sy(v) + 4}' font-size='11' fill='{MUTED}' text-anchor='end'>{v}</text>")
        for v, lab in ((16.7, "16.7 ms = 60 fps"), (25, "25 ms = hitch")):
            svg.append(f"<line x1='{left}' x2='{w - 20}' y1='{sy(v)}' y2='{sy(v)}' stroke='{MUTED}' stroke-width='1'/>"
                       f"<text x='{w - 22}' y='{sy(v) - 4}' font-size='11' fill='{INK2}' text-anchor='end'>{lab}</text>")
        for s in range(0, 28, 5):
            svg.append(f"<text x='{sx(s)}' y='{top + plot_h + 16}' font-size='11' fill='{MUTED}' text-anchor='middle'>{s} s</text>")
        pts = " ".join(f"{sx(x):.1f},{sy(v):.1f}" for x, v in zip(xs, ms))
        svg.append(f"<polyline points='{pts}' fill='none' stroke='{COL[opt]}' stroke-width='2' stroke-linejoin='round' stroke-linecap='round'/></svg>")
        srt = sorted(ms)
        stats = (f"{len(ms)} frames · median {statistics.median(ms):.1f} ms · worst 1% {srt[int(len(srt) * .99)]:.1f} ms · "
                 f"slowest {srt[-1]:.1f} ms · over 25 ms: {sum(v > 25 for v in ms)}")
        panels.append(f"<div class='panel'><h2>{html.escape(LABEL[opt])}</h2><p class='note'>{stats}</p>{''.join(svg)}</div>")
    body = (f"<div class='fig'><h1>Frame pacing at a 60 fps cap: steady in both</h1>"
            f"<p class='sub'>Time per frame across a 27 s run (run 1 of 2), 1280×720, OpenGL ES, expressions changing every 3 s. "
            f"Vsync off with a software cap, because the trial's desktop session wasn't on a monitor (see Limitations). "
            f"Same scale in both panels.</p>{legend(shapes=False)}{''.join(panels)}</div>")
    css = f".panel h2 {{ font-size:14px; margin:8px 0 0 50px; }} .note {{ font-size:12px; color:{INK2}; margin:0 0 0 50px; }}"
    return shoot(pw, page(body, css, palette=f"{COL['A']},{COL['B']}"), out, width=1180, validator=validator)


def marker(opt: str, cx: float, cy: float) -> str:
    if opt == "A":
        return f"<circle cx='{cx}' cy='{cy}' r='7' fill='{COL['A']}' stroke='{SURF}' stroke-width='2'/>"
    return f"<rect x='{cx - 7}' y='{cy - 7}' width='14' height='14' fill='{COL['B']}' stroke='{SURF}' stroke-width='2'/>"


def scores_fig(pw, sc: dict, out: Path, validator: str | None) -> list[str]:
    # Left: weighted totals as bars. Right: per-criterion scores as a dot plot.
    tot = bar_panel("Weighted total", "", sc["totals"], 500, [0, 100, 200, 300, 400, 500], lambda v: f"{v:.0f}",
                    "Out of 500 (Σ weight × score)")
    crit = sc["criteria"]
    w, left, top, row = 620, 230, 26, 34
    sx = lambda s: left + (w - left - 30) * (s - 1) / 4  # noqa: E731
    svg = [f"<svg width='{w}' height='{top + row * len(crit) + 30}'>"]
    for s in range(1, 6):
        svg.append(f"<line x1='{sx(s)}' x2='{sx(s)}' y1='{top - 14}' y2='{top + row * len(crit) - 10}' stroke='{GRID}'/>"
                   f"<text x='{sx(s)}' y='{top + row * len(crit) + 8}' font-size='11' fill='{MUTED}' text-anchor='middle'>{s}</text>")
    for i, (cid, name) in enumerate(crit.items()):
        y = top + i * row
        svg.append(f"<text x='{left - 14}' y='{y + 4}' font-size='13' fill='{INK}' text-anchor='end'>{cid} {html.escape(name)} "
                   f"<tspan fill='{INK2}'>({sc['weights'][cid]})</tspan></text>")
        a, b = sc["scores"]["A"][cid], sc["scores"]["B"][cid]
        if a == b:
            svg.append(marker("A", sx(a), y - 5) + marker("B", sx(b), y + 7))
        else:
            svg.append(f"<line x1='{sx(a)}' x2='{sx(b)}' y1='{y}' y2='{y}' stroke='{GRID}' stroke-width='2'/>")
            svg.append(marker("A", sx(a), y) + marker("B", sx(b), y))
    svg.append(f"<text x='{(left + w - 30) / 2}' y='{top + row * len(crit) + 26}' font-size='11' fill='{INK2}' text-anchor='middle'>"
               f"score (1–5 against the study's written scale)</text></svg>")
    right = f"<div class='panel'><h2>Score per criterion (weight)</h2>{''.join(svg)}</div>"
    body = (f"<div class='fig'><h1>Option A leads by 70 points; no single weight change closes the gap</h1>"
            f"<p class='sub'>Owner's weights (set 2026-11-08). The only criterion where B leads is C3, which would need a weight of 85 "
            f"for B to tie.</p>{legend()}<div class='row'>{tot}{right}</div></div>")
    css = (f".row {{ display:flex; gap:28px; align-items:flex-start; }} .panel h2 {{ font-size:14px; margin:6px 0 0 40px; }}"
           f" .note {{ font-size:12px; color:{INK2}; margin:0 0 0 40px; }}")
    return shoot(pw, page(body, css, palette=f"{COL['A']},{COL['B']}"), out, width=1100, validator=validator)


# ------------------------------------------------------------------ 05 Pi software stack
def stack_fig(pw, out: Path):
    tag = {"m": ("✔ measured on the desktop", "#e7f3e7"), "d": ("📄 documented", "#eef3fb"),
           "u": ("? untested on a Pi", "#fdf1e7"), "n": ("➕ extra layer to install", "#f6f1fb")}
    a = [("eye.py (Python 3.11)", "m", "Eye logic, MQTT via paho, shared/topics.py"),
         ("moderngl, require=310", "m", "Ran on GL 3.1-capped and GLES contexts (Pi-like limits)"),
         ("SDL 2 KMS/DRM driver (inside pygame-ce)", "d", "Present in the bundled SDL; others use it on Pi OS Lite"),
         ("Mesa V3D: OpenGL ES 3.1 / GL 3.1", "d", "Pi 5 GPU driver"),
         ("KMS/DRM → HDMI → projector", "u", "Full-screen, no desktop")]
    b = [("Godot 4.7.2 project (GDScript)", "m", "Eye logic; MQTT needs an add-on or own client"),
         ("Godot Compatibility renderer (GLES 3)", "m", "Ran on opengl3_es here; official arm64 build exists"),
         ("Wayland client", "m", "Godot's display drivers: x11, wayland, headless only"),
         ("cage (kiosk Wayland compositor)", "n", "Needed because Godot has no KMS/DRM driver"),
         ("Mesa V3D: OpenGL ES 3.1 / GL 3.1", "d", "Pi 5 GPU driver"),
         ("KMS/DRM → HDMI → projector", "u", "Full-screen, no desktop")]

    def column(title: str, layers) -> str:
        boxes = "".join(f"<div class='box' style='background:{tag[k][1]}'><b>{html.escape(n)}</b>"
                        f"<span class='why'>{html.escape(w)}</span><span class='tag'>{tag[k][0]}</span></div>" for n, k, w in layers)
        return f"<div class='col'><h2>{title}</h2>{boxes}</div>"

    body = (f"<div class='fig'><h1>How each option would reach the projector on a Pi 5 with no desktop</h1>"
            f"<p class='sub'>Top: our code. Bottom: the screen. Each layer is labelled with how sure we are of it. Option B needs one "
            f"more layer, a compositor, because Godot can't draw straight to the screen.</p>"
            f"<div class='row'>{column('A — Python + moderngl + pygame-ce', a)}{column('B — Godot 4', b)}</div></div>")
    css = (f".row {{ display:flex; gap:28px; align-items:flex-start; }} .col {{ width:520px; }} .col h2 {{ font-size:15px; margin:0 0 8px; }}"
           f" .box {{ border:1px solid {GRID}; border-radius:6px; padding:8px 12px; margin-bottom:6px; display:grid; grid-template-columns:1fr auto; }}"
           f" .box b {{ font-size:13.5px; }} .why {{ grid-column:1; font-size:12px; color:{INK2}; }}"
           f" .tag {{ grid-column:2; grid-row:1 / span 2; align-self:center; font-size:12px; color:{INK}; padding-left:12px; white-space:nowrap; }}")
    shoot(pw, page(body, css), out, width=1150)


# ------------------------------------------------------------------ terminals
TERM_CSS = (".term { background:#1a1a19; color:#f0efec; border-radius:8px; padding:14px 16px; margin:0 0 10px; white-space:pre-wrap; max-width:1150px; }"
            " .term .cmd { color:#86b6ef; } .term .err { color:#ff9a9a; } .term .ok { color:#8fd694; } .term .hd { color:#f5c26b; font-weight:600; }")


def term_html(text: str) -> str:
    out = []
    for ln in text.splitlines():
        e = html.escape(ln)
        if ln.startswith("$"):
            e = f"<span class='cmd'>{e}</span>"
        elif ln.startswith("=="):
            e = f"<span class='hd'>{e}</span>"
        elif ln.startswith(("FAIL", "NONE")) or "RGB wrong" in ln or "ERROR" in ln or "NONE" in ln or "not available" in ln:
            e = f"<span class='err'>{e}</span>"
        elif ln.startswith("OK") or "after the crash" in ln or ln.startswith("mqtt:"):
            e = f"<span class='ok'>{e}</span>"
        out.append(e)
    return "<pre class='term'>" + "\n".join(out) + "</pre>"


def terminal_fig(pw, title: str, sub: str, texts: list[str], out: Path):
    body = f"<div class='fig'><h1>{title}</h1><p class='sub'>{sub}</p>{''.join(term_html(t) for t in texts)}</div>"
    shoot(pw, page(body, TERM_CSS), out, width=1220)


def palette_report(logs: list[str], out: Path) -> None:
    rows = []
    for line in logs:
        try:
            data = json.loads(line)
        except ValueError:
            continue
        if isinstance(data, list):
            for r in data:
                if isinstance(r, dict):
                    rows.append("| " + " | ".join(str(v) for v in r.values()) + " |")
    text = ("# Palette check for the TS-002 charts\n\n"
            f"Run by the dataviz skill's `validate_palette.js` inside the chart pages (light mode, surface `{SURF}`), "
            f"palette `{COL['A']}, {COL['B']}` (A = categorical slot 1, B = slot 2).\n\n"
            "| Check | Result | Detail |\n|---|---|---|\n" + "\n".join(dict.fromkeys(rows)) + "\n")
    if not rows:
        text += "\n(No report captured.)\n" + "\n".join(logs[:20]) + "\n"
    out.write_text(text)


def main() -> int:
    run, scores_json, figs = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    validator = Path(sys.argv[4]).read_text() if len(sys.argv) > 4 else None
    figs.mkdir(parents=True, exist_ok=True)
    res = json.loads((run / "results.json").read_text())
    sc = json.loads(scores_json.read_text())
    logs = lambda n: (run / "logs" / f"{n}.txt").read_text()  # noqa: E731
    with sync_playwright() as pw:
        expressions_fig(pw, run / "screenshots", figs / "01-expressions-a-vs-b.png")
        shader_fig(pw, figs / "02-shader-side-by-side.png")
        console = frames_fig(pw, run, figs / "03-frame-pacing.png", validator)
        console += resources_fig(pw, res, figs / "04-cost-cpu-memory-frame.png", validator)
        stack_fig(pw, figs / "05-pi-software-stack.png")
        terminal_fig(pw, "moderngl at the Pi 5's OpenGL level",
                     "The desktop GPU imitating the Pi's limits: OpenGL capped at 3.1 with MESA_GL_VERSION_OVERRIDE, and an OpenGL ES "
                     "context. moderngl's default request (3.3) fails at 3.1; require=310 works. Read-back must use RGBA on OpenGL ES.",
                     [logs("gl-probes")], figs / "06-gl-probes.png")
        terminal_fig(pw, "Platform checks: display drivers and Pi packages",
                     "Godot has no KMS/DRM display driver. pygame-ce's SDL contains one (it can't start while a desktop owns the screen). "
                     "moderngl and glcontext have no Linux ARM64 wheels, so a Pi compiles them.",
                     [logs("platform-checks")], figs / "07-platform-checks.png")
        terminal_fig(pw, "Both eyes obey MQTT and report online/offline",
                     "Commands sent on the real topics; a malformed message is ignored; a clean exit says offline, and after kill -9 "
                     "the broker publishes the eye's last will (offline).",
                     [logs("mqtt-a"), logs("mqtt-b")], figs / "08-mqtt.png")
        console += scores_fig(pw, sc, figs / "09-scores.png", validator)
    if validator:
        palette_report(console, figs / "palette-validator.md")
    print("figures written to", figs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
