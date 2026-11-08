# monster-house

A friendly animated monster face on the house. Start with `CLAUDE.md` and
`docs/architecture.md`; the current work plan is `docs/stage-0-plan.md`.

## One-time setup (desktop or Raspberry Pi OS)

Python 3.11 is the target (it's what Raspberry Pi OS Bookworm ships).

**On the Ubuntu desktop** (its system Python is newer, so let `uv` fetch 3.11):

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

**On a Pi (Bookworm)**, plain `venv` is enough:

```bash
sudo apt install python3-venv
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Every dependency is pinned in `requirements.txt`.

## Run the tests

```bash
.venv/bin/python -m pytest
```
