"""Make the figures and numbers for docs/results/stage-0-step-4/ from the real brain.

    .venv/bin/python -m tools.results.stage_0_step_4

Runs scripted pretend visits (sim/pretend_visit.py: the real brain, the radar model and
the fake FPP on a pretend clock) and draws what the brain did as SVG timelines. Plain
SVG, so no plotting library is needed; hover a mark for its exact time.
Colors: the dataviz reference palette's categorical slots 1-5, in order, for the moods.
"""

from __future__ import annotations

import json
import math
import tempfile
from html import escape
from pathlib import Path

from shared.messages import eye_commands as eyes
from shared.radar_frame import house_to_radar, in_view
from sim.pretend_visit import ONE_KID, ONE_KID_S, Visit, walk

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT = REPO_ROOT / "docs" / "results" / "stage-0-step-4"

MOOD_COLOR = {"asleep": "#2a78d6", "waking": "#eb6834", "greeting": "#1baf7a",
              "watching": "#eda100", "goodbye": "#e87ba4"}
INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df", "#fcfcfb"
FONT = "font-family='system-ui, sans-serif'"

W, LEFT, RIGHT = 960, 120, 24


class Svg:
    """A tiny SVG writer for timelines: x is seconds."""

    def __init__(self, height: int, seconds: float, title: str) -> None:
        self.h, self.seconds = height, seconds
        self.parts = [f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {W} {height}' "
                      f"width='{W}' height='{height}' {FONT} font-size='13'>",
                      f"<title>{escape(title)}</title>",
                      f"<rect width='{W}' height='{height}' fill='{SURFACE}'/>"]

    def x(self, t: float) -> float:
        return LEFT + (W - LEFT - RIGHT) * t / self.seconds

    def add(self, s: str) -> None:
        self.parts.append(s)

    def text(self, x, y, s, color=INK2, anchor="start", size=13, weight="normal") -> None:
        self.add(f"<text x='{x:.1f}' y='{y:.1f}' fill='{color}' text-anchor='{anchor}' "
                 f"font-size='{size}' font-weight='{weight}'>{escape(s)}</text>")

    def row_label(self, y, s) -> None:
        self.text(LEFT - 10, y + 4, s, INK2, "end")

    def time_axis(self, y: float, top: float, step: int = 5) -> None:
        for t in range(0, int(self.seconds) + 1, step):
            self.add(f"<line x1='{self.x(t):.1f}' x2='{self.x(t):.1f}' y1='{top}' y2='{y}' stroke='{GRID}'/>")
            self.text(self.x(t), y + 16, f"{t}", MUTED, "middle", 12)
        self.text((LEFT + W - RIGHT) / 2, y + 34, "seconds", MUTED, "middle", 12)

    def save(self, path: Path) -> None:
        path.write_text("\n".join(self.parts + ["</svg>"]) + "\n")


def mood_spans(v: Visit, end: float) -> list[tuple[float, float, str]]:
    changes = v.mood_changes()
    return [(t, changes[i + 1][0] if i + 1 < len(changes) else end, m) for i, (t, m) in enumerate(changes)]


def draw_moods(svg: Svg, v: Visit, y: float, end: float) -> None:
    svg.row_label(y + 10, "mood")
    for t0, t1, m in mood_spans(v, end):
        x0, x1 = svg.x(t0), svg.x(t1)
        svg.add(f"<rect x='{x0 + 1:.1f}' y='{y}' width='{max(1, x1 - x0 - 2):.1f}' height='20' rx='4' "
                f"fill='{MOOD_COLOR[m]}'><title>{m}: {t0:.1f}-{t1:.1f} s</title></rect>")
        if x1 - x0 > 60:
            svg.text(x0 + 6, y + 14, m, "#ffffff", size=12, weight="600")


def draw_legend(svg: Svg, y: float) -> None:
    x = LEFT
    for m, c in MOOD_COLOR.items():
        svg.add(f"<rect x='{x}' y='{y - 10}' width='12' height='12' rx='3' fill='{c}'/>")
        svg.text(x + 17, y, m, INK2, size=12)
        x += 30 + 7 * len(m) + 20


def draw_events(svg: Svg, y: float, label: str, events: list[tuple[float, str]], stagger: bool = True) -> None:
    """Labelled markers: a dot at each time, its text above (staggered to avoid overlaps)."""
    svg.row_label(y, label)
    last_x, level = -1e9, 0
    for t, s in events:
        x = svg.x(t)
        level = (level + 1) % 2 if stagger and x - last_x < 8 * len(s) else 0
        last_x = x
        svg.add(f"<circle cx='{x:.1f}' cy='{y}' r='4.5' fill='{INK2}' stroke='{SURFACE}' stroke-width='2'>"
                f"<title>{escape(s)} at {t:.1f} s</title></circle>")
        svg.text(x + 7, y - 6 - 13 * level, s, INK, size=12)


def draw_ticks(svg: Svg, y: float, label: str, times: list[float]) -> None:
    svg.row_label(y + 6, label)
    for t in times:
        svg.add(f"<line x1='{svg.x(t):.1f}' x2='{svg.x(t):.1f}' y1='{y}' y2='{y + 12}' stroke='{INK2}' "
                f"stroke-width='2' stroke-linecap='round'><title>blink at {t:.1f} s</title></line>")


def figure_visit(v: Visit, path: Path) -> dict:
    end = ONE_KID_S
    svg = Svg(470, end, "A pretend visit: one kid walks up, goes to the door, and leaves")
    svg.text(LEFT, 24, "One kid: up the path, to the door (out of the radar's sight), and away",
             INK, size=15, weight="600")
    draw_legend(svg, 50)

    # Kid's distance from the radar, and whether the radar could see them.
    top, bottom, dmax = 80, 200, 7.0
    ypx = lambda d: bottom - (bottom - top) * d / dmax          # noqa: E731
    svg.text(LEFT - 10, top - 6, "kid's distance", INK2, "end")
    for d in (0, 2, 4, 6):
        svg.add(f"<line x1='{LEFT}' x2='{W - RIGHT}' y1='{ypx(d):.1f}' y2='{ypx(d):.1f}' stroke='{GRID}'/>")
        svg.text(LEFT - 10, ypx(d) + 4, f"{d} m", MUTED, "end", 11)
    seen, hidden = [], []
    for t, kids in v.kids_at:
        if not kids:
            continue
        k = kids[0]
        d = math.hypot(k.x - v.site.mount[0], k.y - v.site.mount[1])
        (seen if in_view(*house_to_radar(k.x, k.y, v.site)) and not v.site.door_zone.contains(
            *house_to_radar(k.x, k.y, v.site)) else hidden).append((t, d))
    pts = " ".join(f"{svg.x(t):.1f},{ypx(d):.1f}" for t, d in sorted(seen + hidden))
    svg.add(f"<polyline points='{pts}' fill='none' stroke='{INK2}' stroke-width='2' stroke-linejoin='round'/>")
    if hidden:
        door = [t for t, d in hidden if d < 2]
        x0, x1 = svg.x(min(door)), svg.x(max(door))
        svg.add(f"<rect x='{x0:.1f}' y='{top}' width='{x1 - x0:.1f}' height='{bottom - top}' fill='{INK2}' "
                f"fill-opacity='0.08'><title>at the door, out of the radar's sight</title></rect>")
        svg.text((x0 + x1) / 2, top + 14, "at the door: radar can't see", INK2, "middle", 12)
    svg.text(svg.x(end) - 4, ypx(6.0) - 4, "radar's range", MUTED, "end", 11)

    svg.time_axis(410, 210)
    draw_moods(svg, v, 218, end)
    draw_events(svg, 290, "expression", v.expression_changes())
    draw_events(svg, 350, "voice clip", v.clip_starts())
    draw_ticks(svg, 380, "blink", v.blinks())
    svg.save(path)
    return {"moods": v.mood_changes(), "expressions": v.expression_changes(),
            "clips": v.clip_starts(), "blinks": v.blinks()}


def figure_two_kids(v: Visit, path: Path, a_x: float, b_x: float, end: float) -> dict:
    svg = Svg(320, end, "Two kids: the eyes switch between them")
    svg.text(LEFT, 24, "Two kids standing at the foot of the steps: where the eyes look (x, house m)",
             INK, size=15, weight="600")
    top, bottom = 50, 190
    lo, hi = min(a_x, b_x) - 0.6, max(a_x, b_x) + 0.6
    ypx = lambda x: bottom - (bottom - top) * (x - lo) / (hi - lo)     # noqa: E731
    for x, name in ((a_x, "kid A"), (b_x, "kid B")):
        svg.add(f"<line x1='{LEFT}' x2='{W - RIGHT}' y1='{ypx(x):.1f}' y2='{ypx(x):.1f}' stroke='{GRID}'/>")
        svg.text(LEFT - 10, ypx(x) + 4, f"{name} ({x:+.1f} m)", INK2, "end", 12)
    pts = [(s, lk.x) for s, lk in v.looks() if isinstance(lk, eyes.LookAt)]
    svg.add("<polyline points='" + " ".join(f"{svg.x(s):.1f},{ypx(x):.1f}" for s, x in pts)
            + f"' fill='none' stroke='#2a78d6' stroke-width='2' stroke-linejoin='round'/>")
    switches = [s for (s, x0), (_, x1) in zip(pts, pts[1:]) if abs(x1 - x0) > 1.0]
    for s in switches:
        svg.add(f"<circle cx='{svg.x(s):.1f}' cy='{ypx((a_x + b_x) / 2):.1f}' r='4.5' fill='#2a78d6' "
                f"stroke='{SURFACE}' stroke-width='2'><title>switch at {s:.1f} s</title></circle>")
    svg.time_axis(270, 45)
    draw_moods(svg, v, 205, end)
    draw_ticks(svg, 240, "blink", v.blinks())
    svg.save(path)
    holds = [round(b - a, 1) for a, b in zip(switches, switches[1:])]
    blinks = v.blinks()
    on_switch = sum(1 for s in switches if any(-0.55 < s - b < 0.15 for b in blinks))
    return {"switch_times": switches, "holds_s": holds, "switches_with_a_blink": on_switch,
            "blinks": blinks}


def look_rate(v: Visit, t0: float, t1: float) -> float:
    n = sum(1 for s, lk in v.looks() if t0 <= s < t1 and isinstance(lk, eyes.LookAt))
    return n / (t1 - t0)


def main() -> int:
    (OUT / "figures").mkdir(parents=True, exist_ok=True)
    results: dict = {}
    with tempfile.TemporaryDirectory() as tmp:
        v = Visit(Path(tmp))
        v.run(ONE_KID_S, ONE_KID)
        results["one_kid"] = figure_visit(v, OUT / "figures" / "01-one-kid-visit.svg")
        results["one_kid"]["look_points_per_s_while_watching"] = round(look_rate(v, 10, 14), 1)

        v2 = Visit(Path(tmp))
        a, b = walk(-1.0, 5.5, 2.0, t0=1), walk(1.5, 5.5, 2.0, t0=1.4)
        v2.run(45, lambda t: [a(t), b(t)])
        results["two_kids"] = figure_two_kids(v2, OUT / "figures" / "02-two-kids.svg", -1.0, 1.5, 45)

        v3 = Visit(Path(tmp))
        k = walk(1.0, 5.5, 2.0, t0=1)
        v3.run(12, lambda t: [k(t)])
        before = len(v3.clips())
        v3.radar_status(b"offline")
        t_off = v3.t
        v3.run(30, lambda t: [k(t)])
        results["radar_offline"] = {
            "offline_at": t_off, "moods_after": [m for t, m in v3.mood_changes() if t >= t_off],
            "expressions_after": v3.expressions(since=t_off),
            "last_look": type(v3.looks(since=t_off)[-1][1]).__name__,
            "blinks_in_30_s": len(v3.blinks(since=t_off)), "clips_after": len(v3.clips()) - before}

        v4 = Visit(Path(tmp), fpp=False)
        v4.run(20, lambda t: [k(t)])
        results["no_fpp"] = {"moods": v4.mood_changes(), "fpp_responding": v4.brain.voice.fpp_responding}

    (OUT / "results.json").write_text(json.dumps(results, indent=1) + "\n")
    print(json.dumps({k: {kk: vv for kk, vv in r.items() if kk not in ("blinks", "expressions")}
                      for k, r in results.items()}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
