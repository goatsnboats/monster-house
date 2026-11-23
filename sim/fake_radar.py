"""Fake radar: drag pretend kids around a top-down view of the front of the house, and
publish exactly what the real radar (ESPHome + LD2450) will (ICD-002; SIM-001 to SIM-003).

    .venv/bin/python -m sim.fake_radar

Mouse: click empty ground to add a kid (up to 3) · drag a kid to move them ·
right-click a kid to remove them.
Keys: a add a kid on the sidewalk · Delete/Backspace remove the last kid ·
c clear all · Esc quit.

The view is from above with the house at the top and the street at the bottom, so
"right" on the screen is right as seen from the street (house x, ICD-015). A kid the
radar can't see (behind it, out of range, or in the blind spot by the door) is drawn
hollow. The layout comes from sim/fake_radar.yaml; the radar's position and blind
spot from config/site.yaml.
"""

from __future__ import annotations

import argparse
import logging
import math
import time
from dataclasses import dataclass
from pathlib import Path

import yaml

from shared import topics
from shared.messages import radar_targets as radar
from shared.mqtt_client import DEFAULT_HOST, DEFAULT_PORT, new_client
from shared.radar_frame import (MAX_ANGLE_DEG, MAX_RANGE_MM, SITE_CONFIG, RadarSite, load_radar_site,
                                 radar_to_house)
from sim.radar_model import Kid, RadarModel

log = logging.getLogger("fake_radar")

LAYOUT_FILE = Path(__file__).with_name("fake_radar.yaml")
STATUS_QOS = 0          # ESPHome's defaults (ICD-002): QoS 0, retained
VALUE_QOS = 0
KID_RADIUS_M = 0.25
MAX_KIDS = 3            # SIM-001: up to 3 pretend visitors
KID_NAMES = "ABC"

# Colors (friendly, not spooky)
GRASS = (46, 74, 52)
STREET = (52, 52, 60)
CONCRETE = (150, 146, 138)
STEPS = (120, 112, 104)
PORCH = (110, 82, 60)
HOUSE = (70, 66, 80)
DOOR = (30, 26, 30)
WINDOW = (120, 220, 120)
VIEW_FILL = (255, 230, 120, 28)
VIEW_EDGE = (255, 230, 120)
BLIND = (240, 90, 90, 70)
TEXT = (240, 240, 235)
KID_COLORS = [(255, 150, 60), (120, 200, 255), (240, 120, 220), (200, 230, 90), (255, 220, 90)]


@dataclass(frozen=True)
class Layout:
    view_x: tuple[float, float]
    view_y: tuple[float, float]
    ppm: float
    raw: dict

    @classmethod
    def load(cls, path: Path = LAYOUT_FILE) -> "Layout":
        raw = yaml.safe_load(path.read_text())
        return cls(tuple(raw["view"]["x"]), tuple(raw["view"]["y"]), float(raw["pixels_per_m"]), raw)

    @property
    def size(self) -> tuple[int, int]:
        return (round((self.view_x[1] - self.view_x[0]) * self.ppm),
                round((self.view_y[1] - self.view_y[0]) * self.ppm))

    def to_px(self, x: float, y: float) -> tuple[int, int]:
        return (round((x - self.view_x[0]) * self.ppm), round((y - self.view_y[0]) * self.ppm))

    def to_m(self, px: int, py: int) -> tuple[float, float]:
        return (px / self.ppm + self.view_x[0], py / self.ppm + self.view_y[0])

    def rect(self, xs, ys):
        import pygame
        (x0, y0), (x1, y1) = self.to_px(xs[0], ys[0]), self.to_px(xs[1], ys[1])
        return pygame.Rect(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))


class RadarLink:
    """The MQTT side: online on connect, offline as the last-will, values as given."""

    def __init__(self, host: str, port: int) -> None:
        self.host, self.port = host, port
        self.client = new_client("fake-radar")
        self.client.will_set(topics.RADAR_STATUS, radar.encode("status", "offline"), qos=STATUS_QOS, retain=True)
        self.client.reconnect_delay_set(1, 10)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.connected = False
        self.reconnected = False       # tells the main loop to send every value again

    def start(self) -> None:
        self.client.connect_async(self.host, self.port)
        self.client.loop_start()

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code.is_failure:
            log.warning("broker refused us: %s", reason_code)
            return
        self.connected = self.reconnected = True
        client.publish(topics.RADAR_STATUS, radar.encode("status", "online"), qos=STATUS_QOS, retain=True)
        log.info("connected to %s:%d", self.host, self.port)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties) -> None:
        self.connected = False
        log.warning("lost the broker (%s); retrying", reason_code)

    def publish(self, messages: list[tuple[str, bytes]]) -> None:
        if self.connected:
            for topic, payload in messages:
                self.client.publish(topic, payload, qos=VALUE_QOS, retain=True)

    def stop(self) -> None:
        if self.connected:
            info = self.client.publish(topics.RADAR_STATUS, radar.encode("status", "offline"),
                                       qos=STATUS_QOS, retain=True)
            info.wait_for_publish(timeout=2)
        self.client.disconnect()
        self.client.loop_stop()


# -- drawing -------------------------------------------------------------------------

def eye_windows_from_site(path: Path = SITE_CONFIG) -> dict[str, tuple[float, float]]:
    """Each eye window's center x and width (meters), for drawing; empty if unreadable."""
    try:
        eyes = yaml.safe_load(path.read_text())["eyes"]
        return {side: (float(e["position_m"]["x"]), float(e["window_m"]["w"])) for side, e in eyes.items()}
    except (OSError, KeyError, TypeError, ValueError, yaml.YAMLError):
        return {}


def draw(screen, font, layout: Layout, site: RadarSite, model: RadarModel, kids: list[Kid],
         status: str, eye_windows: dict[str, tuple[float, float]]) -> None:
    import pygame
    L = layout.raw
    w, h = layout.size
    screen.fill(GRASS)
    sw = L["sidewalk_y"]
    screen.fill(CONCRETE, layout.rect(layout.view_x, sw))
    screen.fill(STREET, layout.rect(layout.view_x, (sw[1], layout.view_y[1])))
    screen.fill(CONCRETE, layout.rect(L["walk"]["x"], L["walk"]["y"]))
    screen.fill(STEPS, layout.rect(L["steps"]["x"], L["steps"]["y"]))
    for i in range(1, 4):              # step edges
        y = L["steps"]["y"][0] + i * (L["steps"]["y"][1] - L["steps"]["y"][0]) / 4
        pygame.draw.line(screen, PORCH, layout.to_px(L["steps"]["x"][0], y), layout.to_px(L["steps"]["x"][1], y), 2)
    house = L["house"]
    screen.fill(PORCH, layout.rect(house["porch"]["x"], house["porch"]["y"]))
    screen.fill(HOUSE, layout.rect(house["x"], (layout.view_y[0], house["wall_y"])))
    screen.fill(DOOR, layout.rect(house["door_x"], (house["wall_y"] - 0.12, house["wall_y"])))

    # The eye windows (upstairs, on the wall): where the eyes look from.
    for side, (cx, width) in eye_windows.items():
        r = layout.rect((cx - width / 2, cx + width / 2), (house["wall_y"] - 0.35, house["wall_y"] - 0.1))
        screen.fill(WINDOW, r)
        screen.blit(font.render(f"{side} eye", True, TEXT), (r.x, r.y - 18))

    # What the radar can see, and its blind spot by the door.
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    mount = layout.to_px(*radar_to_house(0, 0, site)[:2])
    arc = [mount]
    for i in range(-MAX_ANGLE_DEG, MAX_ANGLE_DEG + 1, 4):
        a = math.radians(i)
        arc.append(layout.to_px(*radar_to_house(MAX_RANGE_MM * math.sin(a), MAX_RANGE_MM * math.cos(a), site)[:2]))
    pygame.draw.polygon(overlay, VIEW_FILL, arc)
    if site.door_zone:
        z = site.door_zone
        corners = [layout.to_px(*radar_to_house(x, y, site)[:2]) for x, y in ((z.x1, z.y1), (z.x2, z.y2))]
        r = pygame.Rect(min(c[0] for c in corners), min(c[1] for c in corners),
                        abs(corners[1][0] - corners[0][0]), abs(corners[1][1] - corners[0][1]))
        pygame.draw.rect(overlay, BLIND, r)
    screen.blit(overlay, (0, 0))
    pygame.draw.lines(screen, VIEW_EDGE, True, arc, 1)
    if site.door_zone:
        screen.blit(font.render("blind spot", True, TEXT), (r.x + 3, r.y + 3))
    pygame.draw.circle(screen, VIEW_EDGE, mount, 7)
    screen.blit(font.render("radar", True, TEXT), (mount[0] + 9, mount[1] - 8))

    # The kids.
    radius = round(KID_RADIUS_M * layout.ppm)
    for i, kid in enumerate(kids):
        color = KID_COLORS[i % len(KID_COLORS)]
        pos = layout.to_px(kid.x, kid.y)
        slot = model.slot_of(kid)
        pygame.draw.circle(screen, color, pos, radius, 0 if slot else 3)
        label = f"{kid.name} (slot {slot})" if slot else f"{kid.name} (not seen)"
        screen.blit(font.render(label, True, TEXT), (pos[0] + radius + 3, pos[1] - 8))

    # What's being sent.
    lines = [f"MQTT: {status}"]
    for n in range(1, topics.RADAR_MAX_TARGETS + 1):
        vals = [model.values[topics.radar_target(n, f)].sent or "-" for f in topics.RADAR_TARGET_FIELDS]
        lines.append(f"target {n}: x {vals[0]:>6}  y {vals[1]:>6}  speed {vals[2]:>6}")
    lines.append(f"count: {model.values[topics.RADAR_TARGET_COUNT].sent or '-'}")
    lines.append("click: add · drag: move · right-click: remove · a/Del/c · Esc")
    y = h - 18 * len(lines) - 6
    for line in lines:
        screen.blit(font.render(line, True, TEXT), (8, y))
        y += 18


# -- running it ----------------------------------------------------------------------

def parse_args(argv=None):
    p = argparse.ArgumentParser(prog="python -m sim.fake_radar", description=__doc__.split("\n\n")[0])
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--no-mqtt", action="store_true", help="don't connect; just show what would be sent")
    p.add_argument("--layout", type=Path, default=LAYOUT_FILE)
    p.add_argument("--screenshot", type=Path, help="draw one frame with two example kids to a PNG, then quit")
    return p.parse_args(argv)


def kid_at(kids: list[Kid], x: float, y: float) -> Kid | None:
    for kid in reversed(kids):          # the one drawn on top
        if math.hypot(kid.x - x, kid.y - y) <= KID_RADIUS_M * 1.3:
            return kid
    return None


def new_kid(kids: list[Kid], x: float, y: float) -> Kid | None:
    if len(kids) >= MAX_KIDS:
        return None
    used = {k.name for k in kids}
    kid = Kid(x, y, next(n for n in KID_NAMES if n not in used))
    kids.append(kid)
    return kid


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    args = parse_args(argv)
    layout = Layout.load(args.layout)
    site = load_radar_site()
    L = layout.raw
    model = RadarModel(site, L.get("frame_hz", 10), L.get("jitter_mm", 0), L.get("speed_window_s", 0.3))
    kids: list[Kid] = []
    eye_windows = eye_windows_from_site()

    import os
    if args.screenshot:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    pygame.init()
    screen = pygame.display.set_mode(layout.size)
    pygame.display.set_caption("Monster House: fake radar")
    font = pygame.font.Font(None, 22)

    if args.screenshot:
        new_kid(kids, -1.1, 3.4)
        new_kid(kids, 0.8, 5.2)
        new_kid(kids, -1.3, 0.4)        # by the door: in the blind spot
        model.frame(0.0, kids)
        model.frame(0.1, kids)
        draw(screen, font, layout, site, model, kids, "screenshot (not connected)", eye_windows)
        pygame.image.save(screen, str(args.screenshot))
        log.info("saved %s", args.screenshot)
        return 0

    link = None if args.no_mqtt else RadarLink(args.host, args.port)
    if link:
        link.start()

    clock = pygame.time.Clock()
    dragging: Kid | None = None
    s = L["start_spot"]
    running = True
    try:
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_a:
                        new_kid(kids, s["x"], s["y"])
                    elif event.key in (pygame.K_DELETE, pygame.K_BACKSPACE) and kids:
                        kids.pop()
                    elif event.key == pygame.K_c:
                        kids.clear()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    x, y = layout.to_m(*event.pos)
                    hit = kid_at(kids, x, y)
                    if event.button == 1:
                        dragging = hit or new_kid(kids, x, y)
                    elif event.button == 3 and hit:
                        kids.remove(hit)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    dragging = None
                elif event.type == pygame.MOUSEMOTION and dragging:
                    dragging.x, dragging.y = layout.to_m(*event.pos)

            now = time.monotonic()
            if link and link.reconnected:
                link.reconnected = False
                model.resend_all()
            if model.due(now):
                messages = model.frame(now, kids)
                if link:
                    link.publish(messages)
                for topic, payload in messages:
                    log.debug("%s %s", topic, payload.decode())
            status = "off (--no-mqtt)" if not link else ("connected" if link.connected else "waiting for the broker")
            draw(screen, font, layout, site, model, kids, status, eye_windows)
            pygame.display.flip()
            clock.tick(60)
    finally:
        if link:
            link.stop()
        pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
