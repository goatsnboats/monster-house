"""Make the screenshots for the TS-001 results report.

Usage (trial virtual environment with playwright, markdown and pygments, after run_checks.py):

    <venv>/bin/python trials/ts-001/make_figures.py RUN_DIR FIG_DIR [VALIDATOR_JS]

RUN_DIR is run_checks.py's output folder. FIG_DIR receives the PNGs. VALIDATOR_JS is the
dataviz palette validator. If given, it runs inside the chart page and its report is
saved next to the figures.
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import YamlLexer

HERE = Path(__file__).resolve().parent
MERMAID = "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js"

INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#8a8984", "#e1e0d9", "#fcfcfb"
BASE_CSS = f"""
body {{ margin:0; background:{SURF}; color:{INK}; font: 15px/1.45 system-ui, -apple-system, 'Segoe UI', sans-serif; }}
.fig {{ display:inline-block; padding:20px 24px; background:{SURF}; }}
h1 {{ font-size:17px; margin:0 0 4px; }} .sub {{ color:{INK2}; font-size:13px; margin:0 0 14px; }}
pre, code {{ font-family: 'DejaVu Sans Mono', 'Ubuntu Mono', monospace; font-size:12.5px; }}
"""


def page(body: str, css: str = "", head: str = "") -> str:
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{BASE_CSS}{css}</style>{head}</head><body>{body}</body></html>"


def shoot(pw, html_text: str, out: Path, width: int = 1200, wait_mermaid: bool = False,
          url: str | None = None, clip_selector: str = ".fig", full_page: bool = False, script: str | None = None,
          height: int = 900, scale: float = 2):
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": width, "height": height}, device_scale_factor=scale)
    logs: list[str] = []
    pg.on("console", lambda m: logs.append(f"[{m.type}] {m.text}"))
    if url:
        pg.goto(url)
    else:
        pg.set_content(html_text, wait_until="load")
    if script:
        pg.evaluate("console.table = (rows) => console.log(JSON.stringify(rows))")
        pg.add_script_tag(content=script, type="module")
    if wait_mermaid:
        pg.wait_for_function("document.querySelectorAll('pre.mermaid svg').length === document.querySelectorAll('pre.mermaid').length", timeout=30000)
    pg.wait_for_timeout(700)
    if url and not clip_selector:
        pg.screenshot(path=str(out), full_page=full_page)
    else:
        pg.locator(clip_selector).first.screenshot(path=str(out))
    b.close()
    return logs


# ---------------------------------------------------------------- terminal panels
TERM_CSS = """
.term { background:#1a1a19; color:#f0efec; border-radius:8px; padding:14px 16px; margin:0; white-space:pre-wrap; max-width:1100px; }
.term .cmd { color:#86b6ef; } .term .err { color:#ff9a9a; } .term .ok { color:#8fd694; } .term .warn { color:#f5c26b; }
"""


def term_html(text: str) -> str:
    out = []
    for line in text.rstrip().splitlines():
        e = html.escape(line)
        if line.startswith("$ "):
            e = f"<span class='cmd'>{e}</span>"
        elif re.search(r"MISSED|ERROR|error:|FAIL", line):
            e = f"<span class='err'>{e}</span>"
        elif re.search(r"CAUGHT|: OK|exit 0$", line):
            e = f"<span class='ok'>{e}</span>"
        elif "WARNING" in line:
            e = f"<span class='warn'>{e}</span>"
        out.append(e)
    return "<pre class='term'>" + "\n".join(out) + "</pre>"


def terminal_fig(pw, title: str, sub: str, text: str, out: Path):
    shoot(pw, page(f"<div class='fig'><h1>{html.escape(title)}</h1><p class='sub'>{html.escape(sub)}</p>{term_html(text)}</div>", TERM_CSS), out)


# ---------------------------------------------------------------- source comparison
CARD_CSS = f"""
.grid {{ display:grid; grid-template-columns: 1fr 1fr; gap:14px; width:1180px; }}
.card {{ border:1px solid rgba(11,11,11,.10); border-radius:8px; background:#fff; overflow:hidden; }}
.card h2 {{ font-size:14px; margin:0; padding:8px 12px; border-bottom:1px solid {GRID}; background:#f4f3ef; }}
.card .meta {{ color:{INK2}; font-size:12px; padding:6px 12px 0; }}
.card pre {{ margin:0; padding:10px 12px; white-space:pre-wrap; }}
.hl {{ background:#fff3c4; }}
.kw {{ color:#6250d6; font-weight:600; }}
"""


def yaml_block(src: str) -> str:
    return highlight(src, YamlLexer(), HtmlFormatter(nowrap=True))


def plain_block(src: str, keywords: list[str], mark: list[str] = ()) -> str:
    e = html.escape(src)
    for k in keywords:
        e = re.sub(rf"(?<![\w']){re.escape(k)}(?![\w'])", f"<span class='kw'>{k}</span>", e)
    lines = e.splitlines()
    return "\n".join(f"<span class='hl'>{l}</span>" if any(m in l for m in mark) else l for l in lines)


def block_from(text: str, start: str, stop: str) -> str:
    i = text.index(start)
    j = text.find(stop, i + len(start))
    return text[i: j if j > 0 else None].rstrip()


def source_fig(pw, out: Path):
    t = HERE
    a = block_from((t / "a/requirements/brain.yaml").read_text(), "- id: BRN-002", "\n- id:")
    a2 = (t / "a2-doorstop/brn/BRN-002.yml").read_text().rstrip()
    sdoc = (t / "b-strictdoc/requirements.sdoc").read_text()
    b = block_from(sdoc, "[REQUIREMENT]\nUID: BRN-002", "\n\n")
    c_src = (t / "c-sysml/monster.sysml").read_text()
    c_req = block_from(c_src, "        requirement <'BRN-002'>", "\n        requirement <'BRN-003'>")
    c_lines = [l for l in c_src.splitlines() if "publishRate" in l and "requirement" not in l]
    c = c_req + "\n        …\n        #derivation connection {   // parent SYS-001\n            end #original ::> lookAtVisitors;\n" \
        + "            end #derive ::> publishRate;\n        …\n" \
        + "        #derivation connection {   // parent SYS-002\n            end #original ::> reactionTime;\n            end #derive ::> publishRate;\n        …\n" \
        + "\n".join(l for l in c_lines if "satisfy" in l)
    d_sysml = next(l.strip() for l in (t / "d-hybrid/architecture.sysml").read_text().splitlines() if "<'monster-brain'>" in l)
    sysml_kw = ["requirement", "doc", "attribute", "connection", "end", "satisfy", "by", "part", "derivation", "original", "derive"]
    sdoc_kw = ["[REQUIREMENT]", "UID:", "TYPE:", "STATEMENT:", "ALLOCATED_TO:", "VERIFY:", "RELATIONS:", "VALUE:"]
    cards = [
        ("A: YAML (requirements/brain.yaml)", "One block in one file. 7 lines.", yaml_block(a)),
        ("A′: Doorstop item (brn/BRN-002.yml)", "One file per requirement. The hashes are written by Doorstop.", yaml_block(a2)),
        ("B: StrictDoc (requirements.sdoc)", "One block; a blank line ends it. Field names are declared in a 36-line grammar.", plain_block(b, sdoc_kw)),
        ("C: SysML v2 (monster.sysml)", "The text, the two parent links and the allocation sit in 3 places (highlighted).",
         plain_block(c, sysml_kw, mark=["::> publishRate", "satisfy"])),
        ("D: YAML requirement + SysML architecture", "The requirement is identical to A. The component it's allocated to is a SysML part whose short name is the YAML ID.",
         yaml_block(a) + "\n\n<span class='kw'>// architecture.sysml</span>\n" + plain_block(d_sysml, sysml_kw, mark=["<'monster-brain'>"])),
    ]
    cells = "".join(f"<div class='card'><h2>{html.escape(h)}</h2><div class='meta'>{html.escape(m)}</div><pre>{body}</pre></div>" for h, m, body in cards)
    body = (f"<div class='fig'><h1>The same requirement, BRN-002, in each option</h1>"
            f"<p class='sub'>\"The brain shall publish the focus visitor's look point at 10 ± 2 Hz while a visitor is tracked.\" "
            f"Two parents (SYS-001, SYS-002), allocated to the monster brain.</p><div class='grid'>{cells}</div></div>")
    shoot(pw, page(body, CARD_CSS + HtmlFormatter().get_style_defs(".card pre")), out, width=1260)


# ---------------------------------------------------------------- generated trace report (option A)
GH_CSS = f"""
.md {{ width:980px; background:#fff; border:1px solid rgba(11,11,11,.10); border-radius:8px; padding:16px 28px; }}
.md table {{ border-collapse:collapse; font-size:13.5px; }} .md th, .md td {{ border:1px solid #d0d7de; padding:5px 10px; }}
.md th {{ background:#f6f8fa; }} .md h1 {{ font-size:22px; border-bottom:1px solid #d8dee4; padding-bottom:6px; }}
.md h2 {{ font-size:18px; border-bottom:1px solid #d8dee4; padding-bottom:4px; }}
pre.mermaid {{ background:#fff; text-align:center; }}
"""


def trace_fig(pw, md_file: Path, out: Path):
    text = md_file.read_text()
    text = re.sub(r"```mermaid\n(.*?)```", lambda m: f"<pre class=\"mermaid\">\n{html.escape(m.group(1))}</pre>", text, flags=re.S)
    body = markdown.markdown(text, extensions=["tables"])
    head = f"<script src='{MERMAID}'></script><script>window.addEventListener('load',()=>mermaid.run());</script>"
    full = (f"<div class='fig'><h1>Option A: generated traceability report (trace.md)</h1>"
            f"<p class='sub'>Written by check.py --report. Shown with GitHub-like styling; GitHub renders the Mermaid diagrams natively.</p>"
            f"<div class='md'>{body}</div></div>")
    shoot(pw, page(full, GH_CSS, head), out, width=1100, wait_mermaid=True)


# ---------------------------------------------------------------- seeded-error matrix
def matrix_fig(pw, data: dict, out: Path):
    opts = list(data["results"])
    head = "".join(f"<th>{html.escape(o)}</th>" for o in opts)
    rows = ""
    for key, desc in data["errors"].items():
        cells = ""
        for o in opts:
            r = data["results"][o][key]
            if r["caught"]:
                cells += "<td class='y'>✔ caught</td>"
            elif r.get("incidental"):
                cells += "<td class='n'>✖ missed<br><small>only an \"unreviewed edit\" flag</small></td>"
            else:
                cells += "<td class='n'>✖ missed</td>"
        rows += f"<tr><td class='d'>{html.escape(desc)}</td>{cells}</tr>"
    totals = "".join(f"<td class='t'>{sum(v['caught'] for v in data['results'][o].values())} / 6</td>" for o in opts)
    css = f"""
    table {{ border-collapse:separate; border-spacing:0; font-size:14px; }}
    th, td {{ padding:9px 14px; border-bottom:1px solid {GRID}; text-align:center; }}
    th {{ font-weight:600; color:{INK}; border-bottom:2px solid {INK2}; }}
    td.d {{ text-align:left; color:{INK}; }} td.y {{ color:#006300; font-weight:600; }} td.n {{ color:#b42318; font-weight:600; }}
    td.t {{ font-weight:700; font-size:15px; }} small {{ font-weight:400; color:{INK2}; }}
    """
    body = (f"<div class='fig'><h1>Gate G2: seeded-error test</h1><p class='sub'>Each error planted alone in a scratch copy of the sample; "
            f"“caught” means the check exits non-zero and names the problem. Re-run with run_checks.py.</p>"
            f"<table><tr><th style='text-align:left'>Planted error</th>{head}</tr>{rows}<tr><td class='d'><b>Total caught</b></td>{totals}</tr></table>"
            f"<p class='sub' style='margin-top:10px'>C (SysML v2 only) isn't in this table: its validator run is pending. Its resolver would catch a missing parent, but nothing in SysML flags the other five.</p></div>")
    shoot(pw, page(body, css), out, width=1100)


# ---------------------------------------------------------------- score chart (dot plot)
def score_fig(pw, out: Path, validator_js: str | None) -> list[str]:
    sys.path.insert(0, str(HERE))
    import score  # noqa: E402  (trial module: scores and weights)
    opts = ["A", "D", "B", "A'", "C"]
    label = {"A": "A  YAML + own checker", "D": "D  Hybrid", "B": "B  StrictDoc", "A'": "A′ Doorstop", "C": "C  SysML v2"}
    sets = list(score.weights)
    colors = ["#2a78d6", "#eb6834", "#1baf7a"]
    shapes = ["circle", "square", "diamond"]
    tot = {(o, w): sum(a * b for a, b in zip(score.weights[w], score.scores[o])) for o in opts for w in sets}
    x0, x1, left, width, top, rowh = 240, 440, 210, 620, 24, 52
    sx = lambda v: left + (v - x0) / (x1 - x0) * width
    svg = [f"<svg xmlns='http://www.w3.org/2000/svg' width='{left + width + 40}' height='{top + rowh * len(opts) + 50}' font-family='system-ui, sans-serif'>"]
    for v in range(x0, x1 + 1, 20):
        svg.append(f"<line x1='{sx(v)}' y1='{top - 10}' x2='{sx(v)}' y2='{top + rowh * len(opts) - 10}' stroke='{GRID}' stroke-width='1'/>")
        svg.append(f"<text x='{sx(v)}' y='{top + rowh * len(opts) + 12}' font-size='12' fill='{INK2}' text-anchor='middle'>{v}</text>")
    svg.append(f"<text x='{left + width / 2}' y='{top + rowh * len(opts) + 34}' font-size='12' fill='{INK2}' text-anchor='middle'>Weighted total (maximum 500)</text>")
    for i, o in enumerate(opts):
        y = top + i * rowh + rowh / 2 - 10
        svg.append(f"<text x='{left - 14}' y='{y + 4}' font-size='14' fill='{INK}' text-anchor='end'>{html.escape(label[o])}</text>")
        vals = [tot[(o, w)] for w in sets]
        svg.append(f"<line x1='{sx(min(vals))}' y1='{y}' x2='{sx(max(vals))}' y2='{y}' stroke='{GRID}' stroke-width='2'/>")
        for j, w in enumerate(sets):
            cx, cy = sx(tot[(o, w)]), y + (j - 1) * 7  # small vertical offset keeps ties visible
            svg.append(marker(shapes[j], cx, cy, colors[j], f"{o} {w}: {tot[(o, w)]}"))
    # one annotation: the W2 tie between A and D
    ya, yd = top + rowh / 2 - 10, top + rowh + rowh / 2 - 10
    xt = sx(375)
    svg.append(f"<text x='{xt + 14}' y='{(ya + yd) / 2 + 4}' font-size='12' fill='{INK2}'>W2: A and D tie at 375</text>")
    svg.append("</svg>")
    legend = "".join(f"<span class='lg'><svg width='16' height='16'>{marker(shapes[j], 8, 8, colors[j], '')}</svg>{html.escape(w)}</span>" for j, w in enumerate(sets))
    css = ".lg { display:inline-flex; align-items:center; gap:6px; margin-right:18px; font-size:13px; color:#0b0b0b; } .legend { margin:0 0 6px 210px; }"
    body = (f"<div class='fig'><h1>TS-001 weighted totals under the three locked weight sets</h1>"
            f"<p class='sub'>Options sorted by their W1 total. Each row's line spans that option's range across the three weight sets. C and D include provisional (†) scores.</p>"
            f"<div class='legend'>{legend}</div>{''.join(svg)}</div>")
    palette = ",".join(colors)
    html_text = page(body, css).replace("<body>", f"<body data-palette='{palette}' data-mode='light'>")
    return shoot(pw, html_text, out, width=1000, script=validator_js)


def marker(shape: str, cx: float, cy: float, color: str, title: str) -> str:
    ring = f"stroke='{SURF}' stroke-width='2'"
    t = f"<title>{html.escape(title)}</title>" if title else ""
    if shape == "circle":
        return f"<circle cx='{cx}' cy='{cy}' r='6' fill='{color}' {ring}>{t}</circle>"
    if shape == "square":
        return f"<rect x='{cx - 5.5}' y='{cy - 5.5}' width='11' height='11' rx='2' fill='{color}' {ring}>{t}</rect>"
    return f"<path d='M{cx} {cy - 7} L{cx + 7} {cy} L{cx} {cy + 7} L{cx - 7} {cy} Z' fill='{color}' {ring}>{t}</path>"


# ---------------------------------------------------------------- main
def main() -> int:
    run, figs = Path(sys.argv[1]), Path(sys.argv[2])
    validator = Path(sys.argv[3]).read_text() if len(sys.argv) > 3 else None
    figs.mkdir(parents=True, exist_ok=True)
    logs = run / "logs"
    data = json.loads((run / "seeded-errors.json").read_text())
    sd = run / "html/strictdoc/html/b-strictdoc"
    with sync_playwright() as pw:
        source_fig(pw, figs / "01-same-requirement-each-option.png")
        matrix_fig(pw, data, figs / "02-seeded-error-matrix.png")
        terminal_fig(pw, "Option A: checker on the clean sample, plus an impact query",
                     "check.py validates every link and lists what changing SYS-001 would touch.",
                     (logs / "a-clean.txt").read_text(), figs / "03-a-checker-clean.png")
        trace_fig(pw, run / "a-report/trace.md", figs / "04-a-trace-report.png")
        for name, title in [("seeded-a", "Option A: seeded errors, one at a time"),
                            ("seeded-b-strictdoc", "Option B (StrictDoc 0.30.4): seeded errors, one at a time"),
                            ("seeded-a-doorstop", "Option A′ (Doorstop 3.2, --error-all): seeded errors, one at a time"),
                            ("seeded-d-glue", "Option D: glue check (A's checker + SysML short names): seeded errors")]:
            terminal_fig(pw, title, "Exit code and the first error line for each planted error.",
                         (logs / f"{name}.txt").read_text(), figs / f"05-{name}.png")
        shoot(pw, "", figs / "06-strictdoc-document.png", width=1300, url=f"file://{sd}/requirements.html", clip_selector="")
        shoot(pw, "", figs / "07-strictdoc-trace.png", width=2100, height=1100, scale=1.25, url=f"file://{sd}/requirements-TRACE.html", clip_selector="")
        shoot(pw, "", figs / "08-strictdoc-deep-trace.png", width=2100, height=1100, scale=1.25, url=f"file://{sd}/requirements-DEEP-TRACE.html", clip_selector="")
        dpub = run / "html/doorstop"
        shoot(pw, "", figs / "09-doorstop-traceability.png", width=1300, height=700, url=f"file://{dpub}/traceability.html", clip_selector="")
        shoot(pw, "", figs / "09-doorstop-brn-document.png", width=1300, height=1000, url=f"file://{dpub}/documents/BRN.html", clip_selector="")
        churn = (logs / "a2-churn.txt").read_text()
        churn = churn[churn.index("$ git status"):]
        terminal_fig(pw, "Option A′: validating with Doorstop rewrites and stages every item",
                     "Fresh items (links unstamped), committed, then `doorstop` run once to validate. "
                     "Part of the diff is key re-ordering, because the trial converter didn't write Doorstop's order; the hashes and staging are Doorstop's own.",
                     churn, figs / "10-doorstop-churn.png")
        c_src = (HERE / "c-sysml/monster.sysml").read_text()
        excerpt = block_from(c_src, "    package Architecture {", "\n}\n")
        shoot(pw, page(f"<div class='fig'><h1>Option C/D: architecture in SysML v2 text notation (excerpt)</h1>"
                       f"<p class='sub'>Parts, ports, the ICD-001 interface, allocation to hardware and satisfy links. Staged deployment can only be a comment.</p>"
                       f"<div class='card' style='width:1000px'><pre>{plain_block(excerpt, ['package','port','def','part','attribute','interface','end','connect','to','allocate','satisfy','by','doc'], mark=['//'])}</pre></div></div>", CARD_CSS),
              figs / "11-sysml-architecture.png", width=1100)
        console = score_fig(pw, figs / "12-score-dot-plot.png", validator)
    if validator:
        (figs / "12-palette-validator.txt").write_text("\n".join(console) + "\n")
    print("figures:", len(list(figs.glob('*.png'))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
