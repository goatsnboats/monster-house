# Architecture data

> **Status:** Current · **Updated:** 2026-11-18 · **Format:** [ADR 0001](../decisions/0001-requirements-and-architecture-format.md)

- [Components](components.md): every hardware part and software item in the
  [spec tree](../requirements/spec-tree.md), with its subsystem, functions, ports, the
  requirements allocated to it and, for software, which computer it runs on at each stage.
  The page is generated from `components.yaml` (edit that; field meanings are at its top).
- [nodes/](nodes/): one page per computer or controller (each eye Pi, the porch Pi, the
  radar's ESP32, the lip controller, the desktop).
- [software/](software/): one page per software item, including the site config and the
  theme folders.

The checker requires a page for every software item and every part that software runs on.

The prose design is still [../architecture.md](../architecture.md). The interface
documents are in [../interfaces/](../interfaces/).

Check everything with `.venv/bin/python -m tools.reqs.check` (see
[../requirements/README.md](../requirements/README.md)).
