"""The phone page (ICD-004; SHW-023, SHW-030, SHW-031): big buttons and the current mood,
served by the brain itself, with Python's standard library only.

    GET  /            the page (works in any phone browser; add it to the home screen)
    GET  /api/state   {"mood", "muted", "theme", "themes"}
    POST /api/button  {"name": "costume" | "burp" | "sing" | "mute" | "unmute" | "sleep" | "wake"}
    POST /api/theme   {"name": "<theme folder>"}

The server runs in its own thread. It never touches the brain: a press goes into the
brain's inbox, which the brain's loop empties every tick (0.1 s), and the page reads a
copy of the brain's state that the loop refreshes. It listens on 127.0.0.1 only; the
phone reaches it through `tailscale serve` (lighthouse proposal, docs/proposals/).
"""

from __future__ import annotations

import logging
import queue
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from shared.messages import phone_page as icd

log = logging.getLogger("brain.phone")

HOST = "127.0.0.1"          # machine rule: services listen here; the tailnet goes through tailscale serve
PORT = 8080                 # ICD-004, lighthouse docs/ports.md
MAX_BODY = 1024

LABELS = [("costume", "✨ Great costume"), ("burp", "Burp"), ("sing", "Sing"),
          ("mute", "Mute voice"), ("unmute", "Unmute"), ("sleep", "😴 Sleep now"), ("wake", "👀 Wake now")]

PAGE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#1b1430">
<title>Monster House</title>
<style>
  body { margin: 0; font: 18px system-ui, sans-serif; background: #1b1430; color: #f6f2e6; }
  main { max-width: 28rem; margin: 0 auto; padding: 1rem; }
  h1 { font-size: 1.3rem; margin: .25rem 0 1rem; }
  #mood { font-size: 2rem; font-weight: 700; color: #c9b6ff; }
  #muted { color: #ffb35c; min-height: 1.4em; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: .75rem; margin: 1rem 0; }
  button { font: inherit; padding: 1.1rem .5rem; border: 0; border-radius: .9rem;
           background: #7a55e0; color: #fff; touch-action: manipulation; }
  button:active { transform: scale(.97); background: #9374ee; }
  button.wide { grid-column: span 2; background: #c050ff; }
  button.calm { background: #3a2f5c; }
  select { font: inherit; padding: .6rem; border-radius: .6rem; width: 100%; }
  #note { color: #b9b3c9; font-size: .9rem; min-height: 1.2em; }
</style></head>
<body><main>
  <h1>Monster House</h1>
  <div>The monster is <span id="mood">…</span></div>
  <div id="muted"></div>
  <div class="grid">BUTTONS</div>
  <label>Theme <select id="theme"></select></label>
  <p id="note"></p>
</main>
<script>
const $ = (id) => document.getElementById(id);
async function post(path, body) {
  try {
    const r = await fetch(path, {method: "POST", headers: {"Content-Type": "application/json"},
                                 body: JSON.stringify(body)});
    $("note").textContent = r.ok ? "" : "The monster didn't take that (" + r.status + ")";
  } catch (e) { $("note").textContent = "Can't reach the monster"; }
  refresh();
}
async function refresh() {
  try {
    const s = await (await fetch("/api/state")).json();
    $("mood").textContent = s.mood;
    $("muted").textContent = s.muted ? "Voice muted" : "";
    const sel = $("theme");
    if (sel.options.length !== s.themes.length) {
      sel.innerHTML = s.themes.map((t) => `<option>${t}</option>`).join("");
    }
    sel.value = s.theme;
    $("note").textContent = "";
  } catch (e) { $("note").textContent = "Can't reach the monster"; }
}
document.querySelectorAll("button[data-name]").forEach((b) =>
  b.addEventListener("click", () => post("/api/button", {name: b.dataset.name})));
$("theme").addEventListener("change", (e) => post("/api/theme", {name: e.target.value}));
refresh();
setInterval(refresh, 2000);
</script>
</body></html>
"""


def page() -> bytes:
    cls = {"costume": "wide", "sleep": "calm", "wake": "calm"}
    buttons = "".join(f'<button data-name="{n}" class="{cls.get(n, "")}">{label}</button>' for n, label in LABELS)
    return PAGE.replace("BUTTONS", buttons).encode()


class PhonePage:
    """The web server. `inbox` gets ("button", name) and ("theme", name); call
    `set_state` from the brain's loop so the page can show the mood."""

    def __init__(self, inbox: queue.Queue, host: str = HOST, port: int = PORT) -> None:
        self.inbox = inbox
        self._state: dict = {"mood": "asleep", "muted": False, "theme": "", "themes": []}
        self._lock = threading.Lock()
        handler = type("Handler", (_Handler,), {"phone": self})
        self.server = ThreadingHTTPServer((host, port), handler)
        self.port = self.server.server_address[1]
        self._thread = threading.Thread(target=self.server.serve_forever, name="phone-page", daemon=True)

    def start(self) -> None:
        self._thread.start()
        log.info("phone page on http://%s:%d/", *self.server.server_address[:2])

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def set_state(self, state: dict) -> None:
        with self._lock:
            self._state = dict(state)

    def state(self) -> dict:
        with self._lock:
            return dict(self._state)


class _Handler(BaseHTTPRequestHandler):
    phone: PhonePage
    server_version = "MonsterHouse"

    def log_message(self, fmt, *args) -> None:          # quiet: the brain logs the presses
        log.debug(fmt, *args)

    def _send(self, status: HTTPStatus, body: bytes = b"", kind: str = "text/plain; charset=utf-8") -> None:
        self.send_response(status)
        if body:
            self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            self._send(HTTPStatus.OK, page(), "text/html; charset=utf-8")
        elif self.path == "/api/state":
            state = icd.State(**self.phone.state())
            self._send(HTTPStatus.OK, icd.encode("state", state), "application/json")
        else:
            self._send(HTTPStatus.NOT_FOUND, b"not here")

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            self._send(HTTPStatus.BAD_REQUEST, b"too long")
            return
        body = self.rfile.read(length)
        if self.path == "/api/button":
            msg = icd.decode("button", body)
            if msg is None:
                self._send(HTTPStatus.BAD_REQUEST, b"unknown button")
                return
            self.phone.inbox.put(("button", msg.name))
        elif self.path == "/api/theme":
            msg = icd.decode("choose theme", body)
            if msg is None or msg.name not in self.phone.state().get("themes", []):
                self._send(HTTPStatus.BAD_REQUEST, b"unknown theme")
                return
            self.phone.inbox.put(("theme", msg.name))
        else:
            self._send(HTTPStatus.NOT_FOUND, b"not here")
            return
        self._send(HTTPStatus.NO_CONTENT)


def handle(brain, item: tuple[str, str], now: float):
    """Act on one item from the phone in the brain's loop; returns what to publish."""
    kind, name = item
    return brain.press(name, now) if kind == "button" else brain.set_theme(name)

