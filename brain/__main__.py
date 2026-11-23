"""The monster brain. PLACEHOLDER for Stage 0 Step 3: the eyes follow the radar.

    .venv/bin/python -m brain

It listens to the radar (ICD-002) and, about 10 times a second, tells both eyes to look
at the closest visitor (ICD-001 look). With nobody there, or the radar offline, it tells
them to wander (`{"mode": "idle"}`). No moods, blinks or voice yet: those are Step 4,
which replaces this loop with the mood state machine.
"""

from __future__ import annotations

import argparse
import logging
import queue
import time

from brain import gaze
from brain.radar import SUBSCRIPTIONS, RadarState
from shared import topics
from shared.messages import eye_commands as eyes
from shared.mqtt_client import DEFAULT_HOST, DEFAULT_PORT, new_client
from shared.radar_frame import SiteError, load_radar_site

log = logging.getLogger("brain")

LOOK_EVERY_S = 0.1      # about 10 per second while tracking (ICD-001, SHW-009)
LOOK_QOS = 0            # ICD-001


class Brain:
    """The placeholder loop, kept free of MQTT so tests can drive it directly."""

    def __init__(self, site) -> None:
        self.site = site
        self.radar = RadarState()
        self.was_looking: bool | None = None     # None: nothing sent yet

    def tick(self) -> list[tuple[str, bytes]]:
        """What to send now: a look point, or "idle" once when the visitors are gone."""
        point = gaze.look_point(self.radar.targets(), self.site)
        if point is not None:
            self.was_looking = True
            x, y, z = (round(v, 3) for v in point)
            return [(topics.EYES_LOOK, eyes.encode("look", eyes.LookAt(x, y, z)))]
        if self.was_looking is not False:
            self.was_looking = False
            return [(topics.EYES_LOOK, eyes.encode("look", eyes.LookIdle("idle")))]
        return []


def parse_args(argv=None):
    p = argparse.ArgumentParser(prog="python -m brain", description=__doc__.split("\n\n")[0])
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--seconds", type=float, help="quit after this long (for tests)")
    return p.parse_args(argv)


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    args = parse_args(argv)
    try:
        site = load_radar_site()
    except SiteError as err:
        log.error("%s", err)
        return 2
    brain = Brain(site)
    inbox: queue.Queue = queue.Queue()

    client = new_client("brain")
    client.reconnect_delay_set(1, 10)

    def on_connect(c, _u, _f, reason_code, _p):
        if reason_code.is_failure:
            log.warning("broker refused us: %s", reason_code)
            return
        log.info("connected to %s:%d", args.host, args.port)
        c.subscribe([(t, 0) for t in SUBSCRIPTIONS])

    client.on_connect = on_connect
    client.on_message = lambda _c, _u, msg: inbox.put((msg.topic, msg.payload))
    client.connect_async(args.host, args.port)
    client.loop_start()

    radar_was_online = None
    end = time.monotonic() + args.seconds if args.seconds else None
    try:
        while end is None or time.monotonic() < end:
            while True:
                try:
                    brain.radar.update(*inbox.get_nowait())
                except queue.Empty:
                    break
            if brain.radar.online != radar_was_online:
                radar_was_online = brain.radar.online
                log.info("radar %s", "online" if radar_was_online else "offline: the eyes wander")
            for topic, payload in brain.tick():
                client.publish(topic, payload, qos=LOOK_QOS)
            time.sleep(LOOK_EVERY_S)
    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()
        client.loop_stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
