# TS-003 trial: ICD-001's messages, four ways

Throwaway code for [TS-003](../../docs/trades/TS-003-message-schemas.md). Nothing outside
this folder imports it.

- `a_stdlib/`: option A. The ICD is the definition; hand-written dataclasses; `schemas.json`
  written from the ICD by `make_schemas.py` (in the real thing, by the checker).
- `b_pydantic/`: option B, pydantic models (`strict=True`, `extra="forbid"`).
- `c_msgspec/`: option C, msgspec Structs (`forbid_unknown_fields`).
- `d_generated/`: option D. `generate.py` writes `messages.py` from the ICD; `codec.py`
  sends and receives.
- Each option has `drift.py`, the test that fails when its code and the ICD disagree.
- `icd.py`: reads an ICD's messages from its YAML block.
- `schema.py`: a copy of `tools/reqs/schema.py`, the small checker A and D use at run time.
- `shape.py`: compares fields with the ICD, for A, B and C's drift tests.
- `probe.py`: run inside one option's folder; round-trips the ICD examples, feeds bad
  payloads, tries to send bad messages and seeds ICD changes.
- `run_trials.py`: runs the probe for every option, makes the sample change for real,
  measures memory and import time, and writes the report's `results.json` and `logs/`.
- `score.py`: weighted totals and sensitivity.

The report built from these is in
[docs/trades/results/TS-003](../../docs/trades/results/TS-003/README.md).

## Set up (desktop)

A separate virtual environment, so pydantic and msgspec never reach the project's own:

```bash
python3.11 -m venv /tmp/ts003-venv
/tmp/ts003-venv/bin/pip install pydantic==2.14.4 msgspec==0.22.0 PyYAML==6.0.3
```

## Run

From this folder:

```bash
/tmp/ts003-venv/bin/python a_stdlib/make_schemas.py      # A's schemas.json from the ICD
/tmp/ts003-venv/bin/python d_generated/generate.py       # D's messages.py from the ICD
/tmp/ts003-venv/bin/python run_trials.py                 # every measurement (about a minute)
python3 score.py ../../docs/trades/results/TS-003/scores.json
rm -rf /tmp/ts003-venv                                   # /tmp is RAM: clean up
```
