"""Read ICD-001's messages (schema and examples) straight from the ICD's YAML block.

Used by the drift checks, the D generator and run_trials.py; never at run time by a
component. Returns {message name: {"topic", "payload_schema", "examples"}}.
"""

from __future__ import annotations

import copy
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
ICD_001 = ROOT / "docs/interfaces/ICD-001-eye-commands.md"


def messages(path: Path = ICD_001) -> dict:
    for block in re.findall(r"```yaml\n(.*?)```", path.read_text(), re.S):
        data = yaml.safe_load(block)
        if isinstance(data, dict) and "messages" in data:
            return {m["name"]: m for m in data["messages"]}
    raise ValueError(f"no messages: block in {path}")


def changed(icd: dict, edit) -> dict:
    """A deep copy of the ICD messages with `edit(copy)` applied (for seeded mismatches)."""
    new = copy.deepcopy(icd)
    edit(new)
    return new
