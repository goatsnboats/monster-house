"""A scripted pretend visit, without windows or a broker: the real brain, the radar model
(ICD-002) and the fake FPP (ICD-003) on a pretend clock, 10 ticks a second.

    .venv/bin/python -m sim.pretend_visit            # prints the visit's timeline

Used by the brain's tests and by tools/results/stage_0_step_4.py. To watch a visit in
the real windows instead, see brain/README.md.
"""

from __future__ import annotations

import random
import tempfile
from pathlib import Path

from brain.core import Brain
from brain.settings import load_theme_settings
from shared import topics
from shared.messages import eye_commands as eyes
from shared.messages import phone_page
from shared.radar_frame import load_radar_site
from sim.fake_fpp import FakeFpp
from sim.radar_model import Kid, RadarModel

STEP = 0.1


class Visit:
    """Runs the brain, the radar model and the fake FPP together."""

    def __init__(self, audio_dir: Path, fpp: bool = True, seed: int = 4, clip_s: float = 2.5) -> None:
        self.site = load_radar_site()
        self.theme = load_theme_settings("halloween")
        self.brain = Brain(self.site, self.theme, random.Random(seed), any_time=True)
        self.radar = RadarModel(self.site)
        self.fpp = FakeFpp(audio_dir, default_s=clip_s) if fpp else None
        self.t = 0.0
        self.sent: list[tuple[float, str, bytes]] = [(0.0, o.topic, o.payload) for o in self.brain.start(0.0)]
        self.kids_at: list[tuple[float, list[Kid]]] = []     # what the radar model was given
        self.radar_status(b"online")

    def radar_status(self, status: bytes) -> None:
        self.brain.on_message(topics.RADAR_STATUS, status, self.t)

    def run(self, seconds: float, kids=lambda t: []) -> None:
        end = self.t + seconds
        while self.t < end - 1e-9:
            self.t = round(self.t + STEP, 6)
            now_kids = kids(self.t)
            self.kids_at.append((self.t, now_kids))
            for topic, payload in self.radar.frame(self.t, now_kids):
                self.brain.on_message(topic, payload, self.t)
            if self.fpp:
                for topic, payload in self.fpp.tick(self.t):
                    self.brain.on_message(topic, payload, self.t)
            for o in self.brain.tick(self.t):
                self.sent.append((self.t, o.topic, o.payload))
                name = topics.fpp_playlist_from_start(o.topic)
                if name and self.fpp:
                    for topic, payload in self.fpp.start(name, self.t):
                        self.brain.on_message(topic, payload, self.t)

    # What the brain sent, decoded.
    def mood_changes(self) -> list[tuple[float, str]]:
        return [(s, phone_page.decode("mood", p).mood) for s, t, p in self.sent if t == topics.STATE]

    def moods(self) -> list[str]:
        return [m for _, m in self.mood_changes()]

    def expression_changes(self, since: float = 0.0) -> list[tuple[float, str]]:
        return [(s, eyes.decode("expression", p).name) for s, t, p in self.sent
                if t == topics.EYES_EXPRESSION and s >= since]

    def expressions(self, since: float = 0.0) -> list[str]:
        return [n for _, n in self.expression_changes(since)]

    def looks(self, since: float = 0.0) -> list[tuple[float, object]]:
        return [(s, eyes.decode("look", p)) for s, t, p in self.sent if t == topics.EYES_LOOK and s >= since]

    def blinks(self, since: float = 0.0) -> list[float]:
        return [s for s, t, _ in self.sent if t == topics.EYES_BLINK and s >= since]

    def clip_starts(self) -> list[tuple[float, str]]:
        return [(s, n) for s, t, _ in self.sent if (n := topics.fpp_playlist_from_start(t))]

    def clips(self) -> list[str]:
        return [n for _, n in self.clip_starts()]


def walk(x: float, y0: float, y1: float, t0: float, speed: float = 1.0):
    """A kid walking straight from y0 to y1 (house m) at `speed` m/s, starting at t0."""
    def at(t: float) -> Kid:
        d = max(0.0, t - t0) * speed
        return Kid(x, y0 - d if y1 < y0 else y0 + d) if d < abs(y1 - y0) else Kid(x, y1)
    return at


def path(*keys: tuple[float, float, float]):
    """A kid moving in straight lines between keyframes (t, x, y), standing still between
    equal points, and gone after the last one."""
    def at(t: float) -> list[Kid]:
        if t < keys[0][0] or t > keys[-1][0]:
            return []
        for (t0, x0, y0), (t1, x1, y1) in zip(keys, keys[1:]):
            if t0 <= t <= t1:
                f = (t - t0) / (t1 - t0) if t1 > t0 else 1.0
                return [Kid(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f)]
        return []
    return at


# The Step 4 story (seconds, house meters): a kid walks up the path, waits, goes to the
# door for candy (out of the radar's sight), comes back and walks off down the street.
ONE_KID = path((3, 1.0, 5.5), (6.5, 1.0, 2.0), (12, 1.0, 2.0), (15, -1.1, 0.4),
               (24, -1.1, 0.4), (30, -1.1, 6.5))
ONE_KID_S = 60


def one_kid_visit(v: Visit) -> None:
    v.run(ONE_KID_S, ONE_KID)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        v = Visit(Path(tmp))
        one_kid_visit(v)
    events = ([(t, f"mood       {m}") for t, m in v.mood_changes()]
              + [(t, f"expression {e}") for t, e in v.expression_changes()]
              + [(t, f"clip       {c}") for t, c in v.clip_starts()]
              + [(t, "blink") for t in v.blinks()])
    for t, text in sorted(events, key=lambda e: e[0]):
        print(f"{t:6.1f} s  {text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
