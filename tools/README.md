# tools/ — project tools (not shipped to the house)

- `reqs/`: the requirements traceability checker (ADR 0001). It checks
  `docs/requirements/`, `docs/architecture/components.yaml` and `docs/interfaces/`, and
  regenerates `docs/requirements/trace.md`.

## How to run it

From the repository root:

```bash
.venv/bin/python -m tools.reqs.check              # check, and regenerate trace.md
.venv/bin/python -m tools.reqs.check --no-write   # check only
.venv/bin/python -m tools.reqs.check --strict     # gaps and warnings fail too
.venv/bin/python -m tools.reqs.check --impact SYS-004
.venv/bin/python -m pytest tests/test_reqs_check.py
```

What it checks and what the fields mean: `docs/requirements/README.md`.

| File | Does |
|---|---|
| `reqs/check.py` | Command line: runs the checks, prints findings, writes `trace.md` |
| `reqs/load.py` | Reads the files into plain data |
| `reqs/checks.py` | The checks (errors, gaps, warnings) |
| `reqs/schema.py` | A small JSON-Schema checker for ICD payload examples |
| `reqs/shared_topics.py` | Compares ICD topics with `shared/topics.py` |
| `reqs/trace.py` | Writes `trace.md` |

It grew from the TS-001 trial script (`trials/ts-001/a/check.py`), which stays as it was.
