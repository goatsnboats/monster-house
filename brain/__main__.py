"""The monster brain (Stage 0 Step 4): moods, gaze, blinks and voice clips.

    .venv/bin/python -m brain [--any-time]

It listens to the radar (ICD-002), the eyes' status (ICD-001) and Falcon Player's
status (ICD-003), and about 10 times a second tells the eyes where to look, which
expression to show and when to blink, starts voice clips, and publishes its mood
(ICD-004). The decisions are in brain/core.py and the modules it uses.

Outside the theme's show hours the monster stays asleep (TBD-024); --any-time ignores
them, for trying it out during the day.
"""

from __future__ import annotations

import argparse
import logging
import queue
import time

from brain import phone
from brain.core import SUBSCRIPTIONS, Brain
from brain.settings import DEFAULT_THEME, ThemeError, load_theme_settings
from shared.mqtt_client import DEFAULT_HOST, DEFAULT_PORT, new_client
from shared.radar_frame import SiteError, load_radar_site

log = logging.getLogger("brain")

TICK_S = 0.1            # about 10 look points a second while tracking (ICD-001, SHW-009)


def parse_args(argv=None):
    p = argparse.ArgumentParser(prog="python -m brain", description=__doc__.split("\n\n")[0])
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--theme", default=DEFAULT_THEME)
    p.add_argument("--any-time", action="store_true", help="ignore the theme's show hours")
    p.add_argument("--phone-port", type=int, default=phone.PORT, help="the phone page's port (ICD-004)")
    p.add_argument("--no-phone", action="store_true", help="don't serve the phone page")
    p.add_argument("--seconds", type=float, help="quit after this long (for tests)")
    return p.parse_args(argv)


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    args = parse_args(argv)
    try:
        site = load_radar_site()
        theme = load_theme_settings(args.theme)
    except (SiteError, ThemeError) as err:
        log.error("%s", err)
        return 2
    brain = Brain(site, theme, any_time=args.any_time)
    if not args.any_time:
        log.info("show hours %s (use --any-time to ignore them)", theme.show_hours)
    inbox: queue.Queue = queue.Queue()

    presses: queue.Queue = queue.Queue()
    page = None
    if not args.no_phone:
        try:
            page = phone.PhonePage(presses, port=args.phone_port)
            page.start()
        except OSError as err:                  # port taken: carry on without the page
            log.warning("no phone page: %s", err)

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

    start = time.monotonic()
    end = start + args.seconds if args.seconds else None
    out = brain.start(0.0)
    try:
        while end is None or time.monotonic() < end:
            now = time.monotonic() - start
            while True:
                try:
                    out += brain.on_message(*inbox.get_nowait(), now)
                except queue.Empty:
                    break
            while True:
                try:
                    out += phone.handle(brain, presses.get_nowait(), now)
                except queue.Empty:
                    break
            out += brain.tick(now)
            if page:
                page.set_state(brain.state())
            for o in out:
                client.publish(o.topic, o.payload, qos=o.qos, retain=o.retain)
            out = []
            time.sleep(TICK_S)
    except KeyboardInterrupt:
        pass
    finally:
        if page:
            page.stop()
        client.disconnect()
        client.loop_stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
