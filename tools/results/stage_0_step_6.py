"""Make the figures and numbers for docs/results/stage-0-step-6/ (the phone page).

    .venv/bin/python -m tools.results.stage_0_step_6

Starts the real brain (`python -m brain --any-time`) with its phone page on a spare port,
screenshots the page at a phone's size with the cached headless Chromium, and times
presses of "great costume" from the HTTP request to the eyes' sparkle message on the
broker (SYS-023: within 0.5 s). Needs the broker running.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

from brain.core import COSTUME_S
from shared import topics
from shared.messages import eye_commands as eyes
from shared.mqtt_client import connect, new_client

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT = REPO_ROOT / "docs" / "results" / "stage-0-step-6"
CHROME = next(Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/"
                               "chrome-headless-shell"), None)
PRESSES = 10


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def post(url: str, body: dict) -> int:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status


def main() -> int:
    (OUT / "figures").mkdir(parents=True, exist_ok=True)
    port = free_port()
    url = f"http://127.0.0.1:{port}"
    brain = subprocess.Popen([sys.executable, "-m", "brain", "--any-time", "--phone-port", str(port),
                              "--seconds", str(10 + PRESSES * (COSTUME_S + 0.5))], cwd=REPO_ROOT,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    seen, got = threading.Event(), []

    def on_message(_c, _u, msg):
        m = eyes.decode("expression", msg.payload)
        if m is not None and m.name == "sparkle":
            got.append(time.perf_counter())
            seen.set()

    eye = new_client("results-phone-eye")
    eye.on_message = on_message
    connect(eye)
    eye.subscribe(topics.EYES_EXPRESSION, qos=1)
    eye.loop_start()
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(url + "/api/state", timeout=1).read()
                break
            except OSError:
                time.sleep(0.1)
        time.sleep(0.5)
        post(url + "/api/button", {"name": "wake"})       # so the screenshot shows an awake mood
        time.sleep(2.5)
        if CHROME:
            for name, size in (("01-phone-page.png", "390,844"),):
                subprocess.run([str(CHROME), "--no-sandbox", "--hide-scrollbars", f"--window-size={size}",
                                "--force-device-scale-factor=2", f"--screenshot={OUT / 'figures' / name}",
                                "--virtual-time-budget=3000", url + "/"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60, check=False)
        times = []
        for _ in range(PRESSES):
            seen.clear()
            start = time.perf_counter()
            post(url + "/api/button", {"name": "costume"})
            if seen.wait(2.0):
                times.append(round((got[-1] - start) * 1000, 1))
            time.sleep(COSTUME_S + 0.3)
    finally:
        brain.terminate()
        brain.wait(5)
        eye.disconnect()
        eye.loop_stop()
    results = {"press_to_eyes_ms": times, "max_ms": max(times), "requirement_ms": 500,
               "presses": PRESSES, "answered": len(times), "brain_tick_ms": 100}
    (OUT / "results.json").write_text(json.dumps(results, indent=1) + "\n")
    print(json.dumps(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
