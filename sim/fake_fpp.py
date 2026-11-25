"""Fake Falcon Player: takes the brain's clip starts and answers like FPP will (ICD-003,
SIM-004).

    .venv/bin/python -m sim.fake_fpp [--sound]

For each "start clip" it logs the clip, publishes "playing" and the clip's name, and
publishes "idle" when the clip ends. A clip lasts as long as
themes/<theme>/audio/<clip>.wav, or --clip-seconds if there's no recording yet. With
--sound it plays the .wav through the desktop speakers (with `paplay` or `aplay`).
A new start while a clip plays cuts it off, as a playlist start does in FPP.
"""

from __future__ import annotations

import argparse
import logging
import queue
import shutil
import subprocess
import time
import wave
from pathlib import Path

from shared import topics
from shared.messages import clips as icd
from shared.mqtt_client import DEFAULT_HOST, DEFAULT_PORT, new_client

log = logging.getLogger("fake_fpp")

THEMES_DIR = Path(__file__).resolve().parent.parent / "themes"
STATUS_QOS = 0          # ICD-003: player status and playlist playing are QoS 0, retained


def clip_seconds(audio: Path, default: float) -> float:
    """How long a clip plays: its .wav's length, or `default` if there's no readable file."""
    try:
        with wave.open(str(audio), "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except (OSError, wave.Error, EOFError):
        return default


class FakeFpp:
    """The player, kept free of MQTT so tests can drive it with a pretend clock."""

    def __init__(self, audio_dir: Path, default_s: float = 3.0, sound: bool = False) -> None:
        self.audio_dir = audio_dir
        self.default_s = default_s
        self.sound = sound
        self.clip: str | None = None
        self.ends_at = 0.0
        self._player: subprocess.Popen | None = None
        self._command = next((c for c in ("paplay", "aplay") if shutil.which(c)), None) if sound else None
        if sound and self._command is None:
            log.warning("no paplay or aplay found: playing silently")

    def start(self, name: str, now: float) -> list[tuple[str, bytes]]:
        """A start clip arrived: what to publish."""
        self._stop_sound()
        audio = self.audio_dir / f"{name}.wav"
        length = clip_seconds(audio, self.default_s)
        self.clip, self.ends_at = name, now + length
        log.info("start %s (%.1f s%s)", name, length, "" if audio.exists() else ", no recording yet")
        if self._command and audio.exists():
            self._player = subprocess.Popen([self._command, str(audio)],
                                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return [(topics.FPP_STATUS, icd.encode("player status", "playing")),
                (topics.FPP_PLAYLIST_PLAYING, icd.encode("playlist playing", name))]

    def tick(self, now: float) -> list[tuple[str, bytes]]:
        """What to publish now: "idle" once the clip has ended."""
        if self.clip is not None and now >= self.ends_at:
            log.info("done %s", self.clip)
            self.clip = None
            self._stop_sound()
            return [(topics.FPP_STATUS, icd.encode("player status", "idle"))]
        return []

    def _stop_sound(self) -> None:
        if self._player is not None and self._player.poll() is None:
            self._player.terminate()
        self._player = None


def parse_args(argv=None):
    p = argparse.ArgumentParser(prog="python -m sim.fake_fpp", description=__doc__.split("\n\n")[0])
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--theme", default="halloween")
    p.add_argument("--clip-seconds", type=float, default=3.0, help="length of a clip with no recording")
    p.add_argument("--sound", action="store_true", help="play the theme's .wav files")
    p.add_argument("--seconds", type=float, help="quit after this long (for tests)")
    return p.parse_args(argv)


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    args = parse_args(argv)
    fpp = FakeFpp(THEMES_DIR / args.theme / "audio", args.clip_seconds, args.sound)
    inbox: queue.Queue = queue.Queue()
    client = new_client("fake-fpp")
    client.reconnect_delay_set(1, 10)

    def on_connect(c, _u, _f, reason_code, _p):
        if reason_code.is_failure:
            log.warning("broker refused us: %s", reason_code)
            return
        log.info("connected to %s:%d", args.host, args.port)
        c.subscribe(topics.FPP_PLAYLIST_START_ALL, qos=1)
        c.publish(topics.FPP_STATUS, icd.encode("player status", "idle"), qos=STATUS_QOS, retain=True)

    client.on_connect = on_connect
    client.on_message = lambda _c, _u, msg: inbox.put(msg.topic)
    client.connect_async(args.host, args.port)
    client.loop_start()
    end = time.monotonic() + args.seconds if args.seconds else None
    try:
        while end is None or time.monotonic() < end:
            now = time.monotonic()
            out = []
            while True:
                try:
                    name = topics.fpp_playlist_from_start(inbox.get_nowait())
                except queue.Empty:
                    break
                if name:
                    out += fpp.start(name, now)
            out += fpp.tick(now)
            for topic, payload in out:
                client.publish(topic, payload, qos=STATUS_QOS, retain=True)
            time.sleep(0.05)
    except KeyboardInterrupt:
        pass
    finally:
        fpp._stop_sound()
        client.disconnect()
        client.loop_stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
