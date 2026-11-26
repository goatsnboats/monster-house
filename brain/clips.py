"""Voice clips: pools, the minimum gap, and knowing when a clip has finished
(SHW-016, SHW-017, SHW-020, SHW-026, SHW-018 for FPP not answering).

The brain starts a clip by name (ICD-003 "start clip"); Falcon Player, or the fake one,
answers "playing" and then "idle" when the clip ends. `Voice` keeps that state for the
moods: `say` starts a clip if it's allowed now, `busy` is true until it has finished.

If FPP doesn't answer within FPP_ANSWER_S, the brain treats it as not responding: the
clip counts as finished, so the moods carry on with the eyes only.
"""

from __future__ import annotations

import logging
import random

log = logging.getLogger("brain.clips")

FPP_ANSWER_S = 2.0       # no "playing" this long after a start: FPP isn't responding (TBD-023)


class ClipPool:
    """One pool's clips in shuffled order, none repeated until all have played (SHW-016).
    A new round never starts with the clip that ended the last one."""

    def __init__(self, clips: list[str], rng: random.Random) -> None:
        self.clips = list(dict.fromkeys(clips))       # no duplicates
        self.rng = rng
        self._round: list[str] = []
        self._last: str | None = None

    def next(self) -> str | None:
        if not self.clips:
            return None
        if not self._round:
            self._round = self.clips[:]
            self.rng.shuffle(self._round)
            if len(self._round) > 1 and self._round[0] == self._last:
                self._round.append(self._round.pop(0))
        self._last = self._round.pop(0)
        return self._last


class Voice:
    def __init__(self, pools: dict[str, list[str]], min_gap_s: float,
                 rng: random.Random | None = None) -> None:
        rng = rng or random.Random()
        self.pools = {name: ClipPool(clips, rng) for name, clips in pools.items()}
        self.min_gap_s = min_gap_s
        self.muted = False                 # SHW-020 (the phone's mute, Step 6)
        self.fpp_responding = True
        self._starts: list[str] = []       # clips to send to FPP
        self._clip: str | None = None      # started, not yet finished
        self._started_at = 0.0
        self._playing = False              # FPP has said "playing"
        self._ended_at: float | None = None

    def say(self, pool: str, now: float, keep_gap: bool = True) -> bool:
        """Start the next clip from `pool` if allowed now; True if one started."""
        self._check_answer(now)
        if self.muted or self._clip is not None:
            return False
        if keep_gap and self._ended_at is not None and now - self._ended_at < self.min_gap_s:
            return False
        p = self.pools.get(pool)
        name = p.next() if p else None
        if name is None:
            return False
        self._clip, self._started_at, self._playing = name, now, False
        self._starts.append(name)
        log.info("clip %s (%s)", name, pool)
        return True

    def busy(self, now: float) -> bool:
        self._check_answer(now)
        return self._clip is not None

    def take_starts(self) -> list[str]:
        """The clips to start on FPP since the last call."""
        out, self._starts = self._starts, []
        return out

    def on_status(self, status: str, now: float) -> None:
        """FPP's player status (ICD-003): "playing" or "idle"."""
        if not self.fpp_responding:
            log.info("FPP is answering again")
        self.fpp_responding = True
        if status == "playing":
            self._playing = True
        elif status == "idle" and self._clip is not None and self._playing:
            self._finish(now)

    def _check_answer(self, now: float) -> None:
        if self._clip is not None and not self._playing and now - self._started_at >= FPP_ANSWER_S:
            if self.fpp_responding:
                log.warning("FPP didn't start %s: carrying on without voice", self._clip)
            self.fpp_responding = False
            self._finish(now)

    def _finish(self, now: float) -> None:
        self._clip = None
        self._playing = False
        self._ended_at = now
