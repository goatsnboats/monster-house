# TS-001 trials — the same sample in each option

Throwaway evidence for [TS-001](../../docs/trades/TS-001-requirements-approach.md).
Nothing outside this folder may import from it.

**The sample, identical in every option:**
- **Requirements:** 3 system (SYS-001 functional, SYS-002 performance, SYS-003
  constraint) and 7 subsystem (BRN-001…003, EYE-001…004), covering every type.
- **Components:** 2 software (monster brain, eye renderer) and 3 hardware nodes
  (desktop, porch Pi, left eye pod), with deployment by stage.
- **ICD-001:** brain → eyes, `monster/eyes/look`.

| Folder | Option |
|---|---|
| `a/` | A: YAML + Markdown, our own checker (`a/check.py`) |
| `a2-doorstop/` | A′: A's requirements kept in Doorstop instead of our own checker |
| `b-strictdoc/` | B: StrictDoc |
| `c-sysml/` | C: SysML v2 text notation for everything |
| `d-hybrid/` | D: SysML v2 architecture + A's YAML requirements |

`run_checks.sh` repeats every check, including the seeded-error tests. The tools live in a
scratch virtual environment and are not part of the repo (see the script's header).
