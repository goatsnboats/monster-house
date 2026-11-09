# Architecture data

> **Status:** Current · **Updated:** 2026-11-09 · **Format:** [ADR 0001](../decisions/0001-requirements-and-architecture-format.md)

- [components.yaml](components.yaml): every hardware part and software item in the
  [spec tree](../requirements/spec-tree.md), with its subsystem, functions, ports and,
  for software, which computer it runs on at each stage (`deployed_on`). Requirements are
  allocated to these IDs. Field meanings are at the top of the file.
- `nodes/` and `software/` (from STOP 2 of the requirements baseline): one short page per
  hardware node and per software component.

The prose design is still [../architecture.md](../architecture.md). The interface
documents are in [../interfaces/](../interfaces/).

Check everything with `.venv/bin/python -m tools.reqs.check` (see
[../requirements/README.md](../requirements/README.md)).
