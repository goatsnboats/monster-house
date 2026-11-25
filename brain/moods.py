"""The monster's moods (architecture §3b "Moods"; SHW-001 to SHW-005, SHW-015, SHW-018,
SHW-019, SHW-022).

    Asleep -> Waking -> Greeting -> Watching -> Goodbye -> Asleep (or back to Greeting)

The machine is plain Python driven by a clock (`now`, in seconds), so the tests can play
a whole visit in a few milliseconds. Each `tick` gets what the brain senses (is anyone
here, is someone coming) and returns what to do: change mood, change expression, blink.
Where the eyes look is the `look` attribute ("idle", "focus" or "hold"); the gaze code
turns it into look points. Voice clips go through a `Voice` (brain/clips.py), which keeps
the minimum gap and knows when a clip has finished.

The timings come from the theme (SHW-027). The few numbers below are how the face moves
between moods, not show timings; tune them in the simulator.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from brain.settings import Timing

EXPRESSION_MS = 400        # how long the eyes take to ease into a new expression
LOOK_AROUND_S = 1.5        # Waking: look around this long before locking on
NO_CLIP_HOLD_S = 2.5       # Waking/Greeting with no clip (muted, empty pool): hold this long
DROOP_AFTER_S = 2.0        # Goodbye: look where they left this long, then droop
FLUTTER_S = 1.2            # Asleep: a droopy flutter (half-open) this long, with each snore


class Mood(str, Enum):
    ASLEEP = "asleep"
    WAKING = "waking"
    GREETING = "greeting"
    WATCHING = "watching"
    GOODBYE = "goodbye"


# The expression for each mood (ICD-001 names). A matter of taste: review in the simulator.
MOOD_EXPRESSION = {
    Mood.ASLEEP: "asleep",
    Mood.WAKING: "neutral",       # eyes blink open and look around
    Mood.GREETING: "happy",       # happy squint
    Mood.WATCHING: "happy",
    Mood.GOODBYE: "neutral",      # then "sleepy" after DROOP_AFTER_S
}
AMBIENT_EXPRESSION = "neutral"    # radar offline: eyes open, wander and blink


class Voice(Protocol):
    """What the moods need from the clip player (brain/clips.py)."""

    def say(self, pool: str, now: float, keep_gap: bool = True) -> bool:
        """Start a clip from `pool` if allowed now; True if one started."""

    def busy(self, now: float) -> bool:
        """True while a clip is playing (or starting)."""


@dataclass(frozen=True)
class Senses:
    """What the brain knows about the world at one tick."""
    present: bool = False          # anyone tracked, including a visitor held at the door
    approaching: bool = False      # someone coming toward the house, in the approach zone
    radar_online: bool = True
    show_time: bool = True         # inside the theme's show hours (SHW-019)


@dataclass(frozen=True)
class Action:
    kind: str                      # "mood", "expression" or "blink"
    value: str | int               # the mood or expression name, or the blink length in ms


class MoodMachine:
    def __init__(self, timing: Timing, voice: Voice, rng: random.Random | None = None) -> None:
        self.timing = timing
        self.voice = voice
        self.rng = rng or random.Random()
        self.mood = Mood.ASLEEP
        self.look = "idle"             # "idle" (wander), "focus" (follow), "hold" (last point)
        self.ambient = False           # radar offline during show hours
        self.quiet = False             # no voice (outside show hours)
        self._entered = 0.0
        self._last_present = 0.0
        self._spoke = False            # did this mood's clip start?
        self._drooped = False
        self._next_blink = 0.0
        self._next_comment = 0.0
        self._next_snore = 0.0
        self._flutter_until: float | None = None
        self._out: list[Action] = []

    # ── Public ────────────────────────────────────────────────────────────────────

    def start(self, now: float) -> list[Action]:
        """The first actions: asleep, eyes closed."""
        self._enter(Mood.ASLEEP, now)
        return self._flush()

    @property
    def awake(self) -> bool:
        """True when the eyes are open and the brain should blink them (SHW-015)."""
        return self.mood is not Mood.ASLEEP or self.ambient

    def note_blink(self, now: float) -> None:
        """A blink was sent for another reason (a focus switch): restart the blink timer."""
        self._schedule_blink(now)

    def tick(self, now: float, senses: Senses) -> list[Action]:
        if senses.present:
            self._last_present = now
        self.quiet = not senses.show_time
        self._ambient_check(now, senses)

        if self.mood is Mood.ASLEEP:
            self._asleep(now, senses)
        elif self.mood is Mood.WAKING:
            self._waking(now)
        elif self.mood is Mood.GREETING:
            self._greeting(now)
        elif self.mood is Mood.WATCHING:
            self._watching(now)
        elif self.mood is Mood.GOODBYE:
            self._goodbye(now, senses)

        if self.awake and now >= self._next_blink:
            self._out.append(Action("blink", self.timing.blink_ms))
            self._schedule_blink(now)
        return self._flush()

    # ── Each mood ─────────────────────────────────────────────────────────────────

    def _asleep(self, now: float, senses: Senses) -> None:
        if senses.approaching and senses.radar_online and senses.show_time:
            self._enter(Mood.WAKING, now)
            return
        if self.ambient:
            return
        if self._flutter_until is not None and now >= self._flutter_until:
            self._flutter_until = None
            self._expression("asleep")
        if now >= self._next_snore:                      # SHW-002: snore, with a droopy flutter
            self.say("snore", now)
            self._expression("sleepy")
            self._flutter_until = now + FLUTTER_S
            self._next_snore = now + self.timing.snore_every_s

    def _waking(self, now: float) -> None:
        if self._gone_for(now) >= self.timing.goodbye_after_s:
            self._enter(Mood.ASLEEP, now)                # the visitor left before we woke
            return
        elapsed = now - self._entered
        if elapsed >= LOOK_AROUND_S:
            self.look = "focus"                          # lock on
        if self._clip_done(now, elapsed):
            self._enter(Mood.GREETING, now)

    def _greeting(self, now: float) -> None:
        if self._clip_done(now, now - self._entered):
            self._enter(Mood.WATCHING, now)

    def _watching(self, now: float) -> None:
        if self._gone_for(now) >= self.timing.goodbye_after_s:
            self._enter(Mood.GOODBYE, now)
            return
        if now >= self._next_comment and self.say("comment", now):   # SHW-005
            self._next_comment = now + self.rng.uniform(*self.timing.comment_every_s)

    def _goodbye(self, now: float, senses: Senses) -> None:
        if senses.present:
            self._enter(Mood.GREETING, now)              # someone new: no yawn
            return
        elapsed = now - self._entered
        if not self._drooped and elapsed >= DROOP_AFTER_S and not self.voice.busy(now):
            self._drooped = True
            self._expression("sleepy")
        if elapsed >= self.timing.sleep_after_s:
            self._enter(Mood.ASLEEP, now)

    # ── Helpers ───────────────────────────────────────────────────────────────────

    def _enter(self, mood: Mood, now: float) -> None:
        self.mood = mood
        self._entered = now
        self._spoke = False
        self._drooped = False
        self._flutter_until = None
        self._out.append(Action("mood", mood.value))
        if self.ambient and mood is Mood.ASLEEP:
            self._expression(AMBIENT_EXPRESSION)
        else:
            self._expression(MOOD_EXPRESSION[mood])
        self.look = {Mood.ASLEEP: "idle", Mood.WAKING: "idle", Mood.GOODBYE: "hold"}.get(mood, "focus")

        if mood is Mood.ASLEEP:
            self._next_snore = now + self.timing.snore_every_s
        elif mood is Mood.WAKING:
            self._out.append(Action("blink", self.timing.blink_ms))   # blink open
            self._schedule_blink(now)
            self._spoke = self.say("wake", now)
        elif mood is Mood.GREETING:
            # The greeting follows the wake clip at once: it isn't held back by the gap.
            self._spoke = self.say("greet", now, keep_gap=False)
        elif mood is Mood.WATCHING:
            self._next_comment = now + self.rng.uniform(*self.timing.comment_every_s)
        elif mood is Mood.GOODBYE:
            self._spoke = self.say("bye", now)

    def _ambient_check(self, now: float, senses: Senses) -> None:
        """Radar offline: no visits, eyes open and wandering in show hours (SHW-018)."""
        want = not senses.radar_online and senses.show_time
        if not senses.radar_online and self.mood is not Mood.ASLEEP:
            self.ambient = want
            self._enter(Mood.ASLEEP, now)
            return
        if want != self.ambient:
            self.ambient = want
            self._flutter_until = None
            self._expression(AMBIENT_EXPRESSION if want else "asleep")
            if want:
                self._schedule_blink(now)
            else:
                self._next_snore = now + self.timing.snore_every_s

    def _clip_done(self, now: float, elapsed: float) -> bool:
        if self._spoke:
            return elapsed >= LOOK_AROUND_S and not self.voice.busy(now) if self.mood is Mood.WAKING \
                else not self.voice.busy(now)
        return elapsed >= NO_CLIP_HOLD_S

    def _gone_for(self, now: float) -> float:
        return now - self._last_present

    def say(self, pool: str, now: float, keep_gap: bool = True) -> bool:
        """Start a clip unless the monster should be quiet (outside show hours, ambient)."""
        if self.quiet or self.ambient:
            return False
        return self.voice.say(pool, now, keep_gap=keep_gap)

    def _expression(self, name: str) -> None:
        self._out.append(Action("expression", name))

    def _schedule_blink(self, now: float) -> None:
        self._next_blink = now + self.rng.uniform(*self.timing.blink_every_s)

    def _flush(self) -> list[Action]:
        out, self._out = self._out, []
        return out
