"""Repeat every TS-002 measurement and write logs, frame timings, screenshots and results.json.

Usage (from the repository root, trial venv, a desktop session to draw in):

    trials/ts-002/.venv/bin/python trials/ts-002/run_trials.py RUN_DIR [--display wayland|x11]

Needs: the Godot 4.7.2 editor in trials/ts-002/godot/ (see README). For the MQTT checks, the
development broker on localhost:1883 (deploy/mosquitto/run-dev.sh); without it they are skipped.
The PyPI check needs internet access.

Why vsync is off: Claude's desktop session in the trial wasn't on a monitor, and a hidden
session throttles windows that wait for vsync. Both options therefore run with vsync off,
either capped at 60 fps in software (smoothness, CPU, memory) or uncapped (cost per frame).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PY = str(HERE / ".venv" / "bin" / "python")
GODOT = str(HERE / "godot" / "Godot_v4.7.2-stable_linux.x86_64")
EYE_A = str(HERE / "a" / "eye.py")
PROJECT_B = str(HERE / "b")
sys.path.insert(0, str(REPO))
from shared import topics  # noqa: E402

STATES = [("neutral", []), ("happy", []), ("sparkle", []), ("sleepy", []), ("happy-rot-mirror", ["--mirror", "--rotate90"])]


class Run:
    def __init__(self, out: Path, display: str):
        self.out = out
        self.display = display
        self.results: dict = {"date": time.strftime("%Y-%m-%d"), "display": display}
        for sub in ("logs", "frames", "screenshots"):
            (out / sub).mkdir(parents=True, exist_ok=True)

    # ----- helpers
    def clean(self, text: str) -> str:
        """Strip machine-specific paths from logs."""
        text = text.replace(str(REPO), "<repo>").replace(str(Path.home()), "~")
        return re.sub(r"/tmp/[\w./-]+", "<tmp>", text)

    def log(self, name: str, text: str) -> None:
        (self.out / "logs" / f"{name}.txt").write_text(self.clean(text))

    def env_a(self) -> dict:
        return {**os.environ, "SDL_VIDEODRIVER": self.display}

    def cmd_b(self, extra: list[str], gles: bool = True) -> list[str]:
        return [GODOT, "--path", PROJECT_B, "--display-driver", self.display,
                "--rendering-driver", "opengl3_es" if gles else "opengl3", "--", *extra]

    def run(self, cmd: list[str], env: dict | None = None, timeout: float = 60) -> tuple[str, bool]:
        """Run a command; returns (output, exited_by_itself). Kills it if it outlives the timeout."""
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env or os.environ)
        try:
            out, _ = p.communicate(timeout=timeout)
            return out, True
        except subprocess.TimeoutExpired:
            p.kill()
            out, _ = p.communicate()
            return out, False

    @staticmethod
    def summary(output: str) -> dict | None:
        for line in output.splitlines():
            if line.startswith("{") and "frames" in line:
                return json.loads(line)
        return None

    # ----- checks
    def environment(self) -> None:
        info = {
            "python": subprocess.run([PY, "-c", "import sys; print(sys.version.split()[0])"], capture_output=True, text=True).stdout.strip(),
            "packages": subprocess.run([PY, "-c", "from importlib.metadata import version as v; "
                                        "print(*(f'{p}=={v(p)}' for p in ('moderngl', 'glcontext', 'pygame-ce', 'paho-mqtt')))"],
                                       capture_output=True, text=True).stdout.split(),
            "godot": subprocess.run([GODOT, "--version"], capture_output=True, text=True).stdout.strip(),
            "gpu": subprocess.run(["sh", "-c", "lspci | grep -iE 'vga|3d'"], capture_output=True, text=True).stdout.strip(),
            "os": subprocess.run(["sh", "-c", ". /etc/os-release; echo $PRETTY_NAME"], capture_output=True, text=True).stdout.strip(),
        }
        self.results["environment"] = info
        self.log("environment", json.dumps(info, indent=2))

    def gl_probes(self) -> None:
        lines = []
        cases = [
            ("desktop", 330, {}), ("desktop", 310, {"MESA_GL_VERSION_OVERRIDE": "3.1", "MESA_GLSL_VERSION_OVERRIDE": "140"}),
            ("desktop", 330, {"MESA_GL_VERSION_OVERRIDE": "3.1", "MESA_GLSL_VERSION_OVERRIDE": "140"}),
            ("gles30", 310, {}),
        ]
        for mode, req, extra in cases:
            label = " ".join(f"{k}={v}" for k, v in extra.items() if k == "MESA_GL_VERSION_OVERRIDE") or "(no override)"
            out, _ = self.run([PY, str(HERE / "probes" / "gl_probe.py"), mode, str(req)], {**self.env_a(), **extra}, 30)
            line = next((x for x in out.splitlines() if x.startswith(("OK", "FAIL"))), "NO OUTPUT")
            lines.append(f"$ {label} gl_probe.py {mode} {req}\n{line}")
        for mode in ("desktop", "gles30"):
            out, _ = self.run([PY, str(HERE / "probes" / "readback_probe.py"), mode], self.env_a(), 30)
            lines.append(f"$ readback_probe.py {mode}\n" + next((x for x in out.splitlines() if "expected" in x), "NO OUTPUT"))
        text = "\n".join(lines)
        self.results["gl_probes"] = text
        self.log("gl-probes", text)

    def sample(self, pid: int, start: float, end: float, box: dict) -> None:
        """CPU % of one core and peak memory between start and end seconds after launch."""
        hz = os.sysconf("SC_CLK_TCK")
        def cpu() -> float:
            fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
            return (int(fields[11]) + int(fields[12])) / hz
        try:
            time.sleep(start)
            c1, t1, peak = cpu(), time.monotonic(), 0
            while time.monotonic() - t1 < end - start:
                for line in Path(f"/proc/{pid}/status").read_text().splitlines():
                    if line.startswith("VmRSS"):
                        peak = max(peak, int(line.split()[1]))
                time.sleep(0.5)
            box["cpu_pct"] = round(100 * (cpu() - c1) / (time.monotonic() - t1), 2)
            box["peak_rss_mb"] = round(peak / 1024, 1)
        except (FileNotFoundError, ProcessLookupError):
            box["error"] = "process ended early"

    def capped(self, runs: int = 2) -> None:
        """60 fps software cap, 27 s, OpenGL ES: frame pacing + CPU + memory."""
        res = {"A": [], "B": []}
        for r in range(1, runs + 1):
            for opt in ("A", "B"):
                frames = self.out / "frames" / f"{opt.lower()}-capped-run{r}.txt"
                bench = ["--bench", "27", "--no-vsync", "--fps-cap", "60", "--frame-log", str(frames)]
                cmd = [PY, EYE_A, *bench, "--gles"] if opt == "A" else self.cmd_b(bench)
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                     env=self.env_a() if opt == "A" else os.environ)
                box: dict = {}
                t = threading.Thread(target=self.sample, args=(p.pid, 5, 25, box))
                t.start()
                try:
                    out, _ = p.communicate(timeout=60)
                    exited = True
                except subprocess.TimeoutExpired:
                    p.kill()
                    out, _ = p.communicate()
                    exited = False
                t.join()
                entry = {"run": r, **box, "summary": self.summary(out), "exited_by_itself": exited}
                res[opt].append(entry)
                self.log(f"{opt.lower()}-capped-run{r}", out + "\n" + json.dumps(entry, indent=2))
        self.results["capped_60fps"] = res

    def uncapped(self, runs: int = 3) -> None:
        res = {"A": [], "B": [], "B_desktop_gl": []}
        for r in range(1, runs + 1):
            out, ok = self.run([PY, EYE_A, "--bench", "8", "--no-vsync"], self.env_a(), 40)
            res["A"].append({"run": r, "summary": self.summary(out), "exited_by_itself": ok})
            self.log(f"a-uncapped-run{r}", out)
            out, ok = self.run(self.cmd_b(["--bench", "8", "--no-vsync"]), None, 40)
            res["B"].append({"run": r, "summary": self.summary(out), "exited_by_itself": ok})
            self.log(f"b-uncapped-run{r}", out)
        out, ok = self.run(self.cmd_b(["--bench", "8", "--no-vsync"], gles=False), None, 40)
        res["B_desktop_gl"].append({"run": 1, "summary": self.summary(out), "exited_by_itself": ok})
        self.results["uncapped"] = res

    def screenshots(self) -> None:
        shots = self.out / "screenshots"
        res = {}
        for name, extra in STATES:
            expr = name.split("-")[0]
            common = ["--bench", "1.5", "--no-vsync", "--expression", expr, *extra]
            _, ok_a = self.run([PY, EYE_A, *common, "--gles", "--screenshot", str(shots / f"a-{name}.png")],
                               {**self.env_a(), "SDL_VIDEODRIVER": "offscreen"}, 30)
            _, ok_b = self.run(self.cmd_b([*common, "--fps-cap", "60", "--screenshot", str(shots / f"b-{name}.png")]), None, 30)
            res[name] = {"A": (shots / f"a-{name}.png").exists(), "B": (shots / f"b-{name}.png").exists(), "B_exited": ok_b}
        self.results["screenshots"] = res

    def startup(self, runs: int = 3) -> None:
        res = {"A": [], "B": []}
        for _ in range(runs):
            t = time.perf_counter()
            self.run([PY, EYE_A, "--bench", "0.01", "--no-vsync"], self.env_a(), 30)
            res["A"].append(round(time.perf_counter() - t, 3))
            t = time.perf_counter()
            _, ok = self.run(self.cmd_b(["--bench", "0.01", "--no-vsync"]), None, 30)
            res["B"].append(round(time.perf_counter() - t, 3) if ok else None)
        self.results["startup_s"] = res

    def broker_up(self) -> bool:
        try:
            with socket.create_connection(("localhost", 1883), timeout=0.5):
                return True
        except OSError:
            return False

    def mqtt(self) -> None:
        if not self.broker_up():
            self.results["mqtt"] = "skipped: no broker on localhost:1883"
            return
        import paho.mqtt.client as mqtt_lib
        from shared.mqtt_client import connect, new_client

        res = {}
        for opt in ("A", "B"):
            seen: list[str] = []
            watcher = new_client("ts002-watch")
            watcher.on_message = lambda _c, _u, m: seen.append(f"{m.topic} {m.payload.decode()}{' (retained)' if m.retain else ''}")
            connect(watcher)
            watcher.subscribe(topics.EYES_STATUS_ALL)
            watcher.loop_start()
            talker = new_client("ts002-talk")
            connect(talker)
            talker.loop_start()
            transcript = []
            # 1. Commands, then a clean exit.
            cmd = [PY, EYE_A, "--bench", "7", "--no-vsync", "--fps-cap", "60", "--mqtt"] if opt == "A" \
                else self.cmd_b(["--bench", "7", "--no-vsync", "--fps-cap", "60", "--mqtt"])
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                 env=self.env_a() if opt == "A" else os.environ)
            time.sleep(3)
            for topic, payload in ((topics.EYES_BLINK, '{"ms": 180}'),
                                   (topics.EYES_EXPRESSION, '{"name": "happy", "ms": 300}'),
                                   (topics.EYES_EXPRESSION, "not json")):
                talker.publish(topic, payload).wait_for_publish(2)
                transcript.append(f"sent  {topic}  {payload}")
            try:
                out, _ = p.communicate(timeout=25)
                clean_exit = True
            except subprocess.TimeoutExpired:
                p.kill()
                out, _ = p.communicate()
                clean_exit = False
            eye_lines = [x for x in out.splitlines() if x.startswith("mqtt:") or "JSON" in x]
            # 2. Crash: SIGKILL, then read the retained status.
            p2 = subprocess.Popen(cmd[:cmd.index("7")] + ["30"] + cmd[cmd.index("7") + 1:],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                  env=self.env_a() if opt == "A" else os.environ)
            time.sleep(4)
            status_log = list(seen)
            before = seen[-1] if seen else "(nothing)"
            p2.send_signal(signal.SIGKILL)
            p2.wait()
            time.sleep(2)
            after = seen[-1] if seen else "(nothing)"
            for c in (talker, watcher):
                c.disconnect()
                c.loop_stop()
            text = "\n".join([
                f"== {opt}: commands over MQTT",
                *transcript,
                "-- the eye printed:", *eye_lines,
                "-- status messages seen (first run, then the second run starting):", *status_log,
                f"-- crash test: status while running: {before}",
                "   kill -9 the eye ...",
                f"   status after the crash: {after}",
            ])
            res[opt] = {"eye_lines": eye_lines, "clean_exit": clean_exit,
                        "will_after_kill": after.split(" ")[1] if " " in after else after}
            self.log(f"mqtt-{opt.lower()}", text)
        self.results["mqtt"] = res

    def platform_checks(self) -> None:
        lines = []
        out = subprocess.run([GODOT, "--help"], capture_output=True, text=True).stdout
        drivers = re.sub(r"\x1b\[[0-9;]*m", "", next((x for x in out.splitlines() if "--display-driver" in x), ""))
        lines += ["$ godot --help | grep -- --display-driver", drivers.strip()]
        out, _ = self.run([PY, "-c", "import pygame\ntry:\n    pygame.display.init(); print('kmsdrm: OK', pygame.display.get_driver())\n"
                           "except Exception as e:\n    print('kmsdrm:', e)"], {**os.environ, "SDL_VIDEODRIVER": "kmsdrm"}, 20)
        lines += ["", "$ SDL_VIDEODRIVER=kmsdrm python -c 'import pygame; pygame.display.init()'",
                  next((x for x in out.splitlines() if x.startswith("kmsdrm")), out.strip())]
        sdl = next((HERE / ".venv").glob("lib/python3.11/site-packages/pygame_ce.libs/libSDL2-2-*"), None)
        if sdl:
            syms = sorted({m for m in re.findall(rb"KMSDRM_[A-Za-z]+", sdl.read_bytes())})[:4]
            lines += ["", "$ strings pygame_ce.libs/libSDL2-2-*.so | grep KMSDRM_", *(s.decode() for s in syms)]
        lines += ["", "$ PyPI: Linux ARM64 (aarch64) wheels for Python 3.11"]
        wheels = {}
        for pkg, ver in (("moderngl", "5.13.0"), ("glcontext", "3.1.0"), ("pygame-ce", "2.5.8")):
            try:
                data = json.load(urllib.request.urlopen(f"https://pypi.org/pypi/{pkg}/{ver}/json", timeout=20))
                arm = [f["filename"] for f in data["urls"] if "aarch64" in f["filename"] and ("cp311" in f["filename"] or "abi3" in f["filename"])]
            except OSError as e:
                arm = [f"(check failed: {e})"]
            wheels[pkg] = arm
            lines.append(f"{pkg} {ver}: {', '.join(arm) if arm else 'NONE - pip must compile it on a Pi'}")
        self.results["platform"] = {"godot_display_drivers": drivers.strip(), "arm64_wheels": wheels}
        self.log("platform-checks", "\n".join(lines))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--display", default="wayland", choices=("wayland", "x11"))
    ap.add_argument("--steps", help="comma-separated subset to re-run, e.g. platform_checks (merged into results.json)")
    args = ap.parse_args()
    r = Run(args.out, args.display)
    steps = [r.environment, r.gl_probes, r.platform_checks, r.capped, r.uncapped, r.screenshots, r.startup, r.mqtt]
    if args.steps:
        old = args.out / "results.json"
        if old.exists():
            r.results.update(json.loads(old.read_text()))
        steps = [s for s in steps if s.__name__ in args.steps.split(",")]
    for step in steps:
        print(f"... {step.__name__}", flush=True)
        step()
        (args.out / "results.json").write_text(r.clean(json.dumps(r.results, indent=2)))
    print(f"done: {args.out / 'results.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
