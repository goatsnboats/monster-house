"""The monster brain, all together, without MQTT (so the tests can drive it).

    radar (ICD-002) -> visitors -> focus -> moods -> eyes (ICD-001), clips (ICD-003),
                                                   -> mood (ICD-004, retained)

`on_message` takes every message the brain subscribes to; `tick` runs about 10 times a
second and returns what to publish. Each module says which requirements it meets; this
one adds the reactions within a visit (SHW-012 to SHW-014), the blink on a focus switch,
and the failure behavior for eyes and radar (SHW-018, SHW-024).
"""

from __future__ import annotations

import datetime as dt
import logging
import random
from typing import NamedTuple

from brain.clips import Voice
from brain.focus import Focus
from brain.gaze import visitor_point
from brain.moods import EXPRESSION_MS, MOOD_EXPRESSION, Action, Mood, MoodMachine, Senses
from brain.radar import RadarState
from brain.settings import ThemeSettings
from brain.visitors import Tracker
from shared import topics
from shared.messages import clips as fpp_icd
from shared.messages import eye_commands as eyes
from shared.messages import phone_page

log = logging.getLogger("brain")

GLANCE_S = 0.8          # SHW-014: a surprised glance at a new kid coming, this long
RECENT_BLINK_S = 0.5    # no blink for a focus switch this soon after another blink
KEEPALIVE_S = 2.0       # re-send the look at least this often, inside the eyes' 5 s fallback

SUBSCRIPTIONS = [topics.RADAR_SENSOR_ALL, topics.RADAR_STATUS, topics.EYES_STATUS_ALL, topics.FPP_STATUS]


class Out(NamedTuple):
    topic: str
    payload: bytes
    qos: int
    retain: bool


class Brain:
    def __init__(self, site, theme: ThemeSettings, rng: random.Random | None = None,
                 any_time: bool = False) -> None:
        rng = rng or random.Random()
        t = theme.timing
        self.site = site
        self.theme = theme
        self.any_time = any_time                     # ignore show hours (development)
        self.radar = RadarState()
        self.tracker = Tracker(site, t.door_hold_s)
        self.focus = Focus(t.focus_hold_s, rng)
        self.voice = Voice(theme.clips, t.min_gap_s, rng)
        self.moods = MoodMachine(t, self.voice, rng)
        self.eyes_online: dict[str, bool] = {}
        self.focus_id: int | None = None
        self._expression: str | None = None
        self._glance_until: float | None = None
        self._look: bytes | None = None              # the last look message sent
        self._look_at = -1e9
        self._radar_was_online: bool | None = None
        self._last_blink = -1e9

    # ── Messages in ───────────────────────────────────────────────────────────────

    def start(self, now: float) -> list[Out]:
        """The first messages: the theme (SHW-021) and asleep."""
        out = [Out(topics.THEME, eyes.encode("theme", eyes.Theme(self.theme.name)), 1, True)]
        return out + self._actions(self.moods.start(now))

    def on_message(self, topic: str, payload: bytes, now: float) -> list[Out]:
        if self.radar.update(topic, payload):
            return []
        if topic == topics.FPP_STATUS:
            status = fpp_icd.decode("player status", payload)
            if status is not None:
                self.voice.on_status(status, now)
            return []
        for side in topics.EYE_SIDES:
            if topic == topics.eye_status(side):
                return self._eye_status(side, eyes.decode("status", payload))
        return []

    def _eye_status(self, side: str, status: str | None) -> list[Out]:
        """An eye dropping out is logged and nothing else changes (SHW-018). One coming
        back is told the current expression and look, so it matches the other eye."""
        if status is None or self.eyes_online.get(side) == (status == "online"):
            return []
        self.eyes_online[side] = status == "online"
        if status == "offline":
            log.warning("%s eye offline: carrying on with the other", side)
            return []
        log.info("%s eye online", side)
        out = []
        if self._expression:
            out.append(Out(topics.EYES_EXPRESSION, eyes.encode("expression", eyes.Expression(self._expression, 0)), 1, False))
        if self._look:
            out.append(Out(topics.EYES_LOOK, self._look, 0, False))
        return out

    # ── Each tick ─────────────────────────────────────────────────────────────────

    def tick(self, now: float, wall: dt.datetime | None = None) -> list[Out]:
        if self.radar.online != self._radar_was_online:
            self._radar_was_online = self.radar.online
            log.info("radar %s", "online" if self.radar.online else "offline: ambient mode")

        targets = [(t.x_mm, t.y_mm) for t in self.radar.targets()]
        events = self.tracker.update(now, targets)
        visitor, switched = self.focus.choose(now, self.tracker, events)
        self.focus_id = visitor.id if visitor else None
        visitors = self.tracker.visitors.values()
        senses = Senses(
            present=bool(self.tracker.visitors),
            approaching=any(v.heading == "coming" and self.tracker.range_m(v) <= self.site.approach_range_m
                            for v in visitors),
            radar_online=self.radar.online,
            show_time=self.any_time or self.theme.in_show_hours(wall or dt.datetime.now()),
        )
        actions = self.moods.tick(now, senses)
        if any(a.kind == "expression" for a in actions):
            self._glance_until = None                # a new mood's face wins over a glance

        # Reactions within a visit, while the monster is greeting or watching.
        if self.moods.mood in (Mood.GREETING, Mood.WATCHING):
            for e in events:
                if e.kind == "coming" and e.visitor.id in self.tracker.visitors:       # SHW-014
                    self.focus.glance(e.visitor, now)
                    switched = switched or self.focus_id not in (None, e.visitor.id)
                    self.focus_id = e.visitor.id
                    actions.append(Action("expression", "surprised"))
                    self._glance_until = now + GLANCE_S
                    self.moods.say("arrival", now)
                elif e.kind == "going":                                               # SHW-013
                    self.moods.say("bye", now)
                elif e.kind == "at door":                                             # SHW-012
                    self.moods.say("door", now)
        if self._glance_until is not None and now >= self._glance_until:
            self._glance_until = None
            actions.append(Action("expression", MOOD_EXPRESSION[self.moods.mood]))

        if any(a.kind == "blink" for a in actions):
            self._last_blink = now
        elif switched and self.moods.awake and now - self._last_blink >= RECENT_BLINK_S:
            actions.append(Action("blink", self.theme.timing.blink_ms))           # blink on a switch
            self.moods.note_blink(now)
            self._last_blink = now

        out = self._actions(actions)
        out += self._look_out(now)
        out += [Out(topics.fpp_playlist_start(name), b"", 1, False) for name in self.voice.take_starts()]
        return out

    def _look_out(self, now: float) -> list[Out]:
        """Where to look (SHW-009): the focus visitor about 10 times a second; wander; or
        hold the last point (Goodbye, or nobody in sight). Re-sent every KEEPALIVE_S."""
        mode = self.moods.look
        payload = None
        if mode == "idle":
            payload = eyes.encode("look", eyes.LookIdle("idle"))
        elif mode == "focus" and self.focus_id is not None:
            x, y, z = (round(v, 3) for v in visitor_point(self.tracker.visitors[self.focus_id], self.site))
            payload = eyes.encode("look", eyes.LookAt(x, y, z))
            self._look = payload
            self._look_at = now
            return [Out(topics.EYES_LOOK, payload, 0, False)]
        if payload is None:
            payload = self._look                     # hold: keep the last point
        if payload is None or (payload == self._look and now - self._look_at < KEEPALIVE_S):
            return []
        self._look, self._look_at = payload, now
        return [Out(topics.EYES_LOOK, payload, 0, False)]

    def _actions(self, actions: list[Action]) -> list[Out]:
        out = []
        for a in actions:
            if a.kind == "mood":
                log.info("mood: %s", a.value)
                out.append(Out(topics.STATE, phone_page.encode("mood", phone_page.Mood(a.value)), 1, True))
            elif a.kind == "expression":
                if str(a.value) == self._expression:
                    continue                         # already showing it
                self._expression = str(a.value)
                out.append(Out(topics.EYES_EXPRESSION,
                               eyes.encode("expression", eyes.Expression(self._expression, EXPRESSION_MS)), 1, False))
            elif a.kind == "blink":
                out.append(Out(topics.EYES_BLINK, eyes.encode("blink", eyes.Blink(int(a.value))), 0, False))
        return out
