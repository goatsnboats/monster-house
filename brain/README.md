# brain/ — the monster brain

The one place where decisions are made: mood state machine (Asleep → Waking →
Greeting → Watching → Goodbye), gaze math, blinks, clip pools and the phone page.
See `docs/architecture.md` §3b.

**Status:** a placeholder from Stage 0 Step 3. It reads the radar and makes both eyes
look at the closest visitor; with nobody there (or the radar offline) it tells them to
wander. No moods, smoothing, focus rules, blinks or voice yet: Step 4.

## How to run it

With the broker running, from the repository root:

```bash
.venv/bin/python -m brain
```

It sends `monster/eyes/look` about 10 times a second while someone is in view
(ICD-001), and `{"mode": "idle"}` once when they've gone. To see it work, run it with
both eyes and the fake radar (see `sim/README.md`).

## Code

- `radar.py`: puts ESPHome's separate radar values back together into up to three
  targets (ICD-002). An empty slot reads `nan`; silence is normal.
- `gaze.py`: where to look. For now: the target closest to the radar, at head height
  (`config/site.yaml`), with no smoothing.
- `__main__.py`: the loop. Step 4 replaces it with the mood state machine.
