"""Run every TS-003 measurement and write the results report's data and logs.

    /path/to/trial-venv/bin/python run_trials.py

Needs a virtual environment with pydantic, msgspec, PyYAML and pytest (see README.md).
Writes docs/trades/results/TS-003/results.json and logs/.
"""

from __future__ import annotations

import difflib
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "docs/trades/results/TS-003"
OPTIONS = {"A": "a_stdlib", "B": "b_pydantic", "C": "c_msgspec", "D": "d_generated"}
PY = sys.executable
RUNS = 15

sys.path.insert(0, str(HERE))
import icd  # noqa: E402


def run(cmd: list[str], cwd: Path, timeout: int = 120, trial: Path = HERE) -> str:
    env = dict(os.environ, PYTHONPATH=f"{trial}:{cwd}", PYTHONDONTWRITEBYTECODE="1")
    done = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    if done.returncode:
        raise RuntimeError(f"{cmd} in {cwd}: {done.stderr[-2000:]}")
    return done.stdout


# --- G1, G4, C3, G3: the probe, in each option's folder -------------------------------

def probes() -> dict:
    return {opt: json.loads(run([PY, str(HERE / "probe.py")], HERE / folder))
            for opt, folder in OPTIONS.items()}


# --- C1: the sample change, made for real ---------------------------------------------

EASE_LINE = '    ease: Literal["linear", "smooth"]\n'
SAMPLE_EDITS = {  # the hand edit each option needs in its code, after the ICD changes
    "A": ("messages.py", "    name: ExpressionName\n    ms: int\n", "    name: ExpressionName\n    ms: int\n" + EASE_LINE),
    "B": ("messages.py", "    ms: int = Field(ge=0)\n\n\nclass Blink",
          "    ms: int = Field(ge=0)\n" + EASE_LINE + "\n\nclass Blink"),
    "C": ("messages.py", "    name: ExpressionName\n    ms: Milliseconds\n",
          "    name: ExpressionName\n    ms: Milliseconds\n" + EASE_LINE),
    "D": None,  # nothing by hand: generate.py rewrites messages.py
}
ICD_EDIT = (
    "        ms: {type: integer, minimum: 0}\n    examples:\n      - {name: happy, ms: 300}\n",
    "        ms: {type: integer, minimum: 0}\n        ease: {enum: [linear, smooth]}\n"
    "    examples:\n      - {name: happy, ms: 300, ease: smooth}\n",
)


def sample_change() -> dict:
    """Add a required `ease` key to expression in a copy of the repo's ICD and each option."""
    results, diffs = {}, []
    icd_text = icd.ICD_001.read_text()
    assert ICD_EDIT[0] in icd_text
    new_icd = icd_text.replace(ICD_EDIT[0], ICD_EDIT[1]).replace(
        "      required: [name, ms]\n", "      required: [name, ms, ease]\n")
    diffs += difflib.unified_diff(icd_text.splitlines(True), new_icd.splitlines(True),
                                  "a/" + str(icd.ICD_001.relative_to(ROOT)), "b/" + str(icd.ICD_001.relative_to(ROOT)))
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "docs/interfaces").mkdir(parents=True)
        (tmp / "docs/interfaces" / icd.ICD_001.name).write_text(new_icd)
        trial = tmp / "trials/ts-003"
        shutil.copytree(HERE, trial, ignore=shutil.ignore_patterns("__pycache__"))
        for opt, folder in OPTIONS.items():
            where = trial / folder
            hand = 0
            if SAMPLE_EDITS[opt]:
                name, old, new = SAMPLE_EDITS[opt]
                text = (where / name).read_text()
                assert old in text, (opt, old)
                (where / name).write_text(text.replace(old, new, 1))
                diffs += difflib.unified_diff(text.splitlines(True), text.replace(old, new, 1).splitlines(True),
                                              f"a/trials/ts-003/{folder}/{name}", f"b/trials/ts-003/{folder}/{name}")
                hand = 1
            regenerated = []
            if opt == "A":
                run([PY, "make_schemas.py"], where, trial=trial)
                regenerated.append("schemas.json (by the checker)")
            if opt == "D":
                run([PY, "generate.py"], where, trial=trial)
                regenerated.append("messages.py (by generate.py)")
            left = json.loads(run([PY, "-c", "import icd, drift, json; print(json.dumps(drift.drift(icd.messages())))"], where, trial=trial))
            results[opt] = {"files_edited_by_hand": 1 + hand, "code_lines_edited_by_hand": hand,
                            "regenerated": regenerated, "drift_after_change": left}
    (OUT / "logs").mkdir(parents=True, exist_ok=True)
    (OUT / "logs/sample-change.diff").write_text("".join(diffs))
    return results


# --- C4: footprint ----------------------------------------------------------------------

FOOT = r"""
import time, json, importlib.util
t0 = time.perf_counter()
{imports}
t1 = time.perf_counter()
{work}
rss_kb = next(int(l.split()[1]) for l in open("/proc/self/status") if l.startswith("VmRSS:"))
print(json.dumps({{"import_ms": (t1 - t0) * 1000, "rss_kb": rss_kb}}))
"""
WORK = """
api = __import__("codec") if importlib.util.find_spec("codec") else __import__("messages")
for i in range(1000):
    api.decode("look", b'{"x": 1.2, "y": 3.5, "z": 1.0}')
    api.encode("blink", api.decode("blink", b'{"ms": 180}'))
"""


def footprint() -> dict:
    cases = {"baseline (json, logging, dataclasses, typing)": (HERE / "a_stdlib", "import json, logging, dataclasses, typing", "")}
    for opt, folder in OPTIONS.items():
        api = "codec" if opt == "D" else "messages"
        cases[opt] = (HERE / folder, f"import {api}", WORK)
    out = {}
    for label, (cwd, imports, work) in cases.items():
        samples = [json.loads(run([PY, "-c", FOOT.format(imports=imports, work=work)], cwd)) for _ in range(RUNS)]
        out[label] = {"import_ms_median": round(statistics.median(s["import_ms"] for s in samples), 1),
                      "rss_mb_median": round(statistics.median(s["rss_kb"] for s in samples) / 1024, 1)}
    base = out["baseline (json, logging, dataclasses, typing)"]["rss_mb_median"]
    for opt in OPTIONS:
        out[opt]["extra_memory_mb"] = round(out[opt]["rss_mb_median"] - base, 1)
    return out


def install_size() -> dict:
    site = Path(sys.prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"

    def size(*names) -> float:
        total = 0
        for n in names:
            p = site / n
            files = [p] if p.is_file() else p.rglob("*")
            total += sum(f.stat().st_size for f in files if f.is_file() and "__pycache__" not in f.parts)
        return round(total / 1e6, 2)

    return {"A": 0.0, "D": 0.0,
            "B": size("pydantic", "pydantic_core", "typing_extensions.py", "annotated_types", "typing_inspection"),
            "C": size("msgspec")}


# --- C2 (part): how much code each option needs ----------------------------------------

def code_lines() -> dict:
    def count(path: Path) -> int:
        return sum(1 for line in path.read_text().splitlines() if line.strip() and not line.strip().startswith("#"))
    files = {"A": ["messages.py", "drift.py"], "B": ["messages.py", "drift.py"], "C": ["messages.py", "drift.py"],
             "D": ["codec.py", "drift.py", "generate.py"]}
    out = {opt: {f: count(HERE / OPTIONS[opt] / f) for f in fs} for opt, fs in files.items()}
    out["D"]["messages.py (generated)"] = count(HERE / "d_generated/messages.py")
    out["shared by A and D"] = {"schema.py": count(HERE / "schema.py")}
    out["shared by A, B and C drift tests"] = {"shape.py": count(HERE / "shape.py")}
    return out


def pydantic_default_mode() -> dict:
    """What pydantic does WITHOUT strict=True (its default)."""
    code = ("from pydantic import BaseModel, ConfigDict\n"
            "class Blink(BaseModel):\n    model_config = ConfigDict(extra='forbid')\n    ms: int\n"
            "print(Blink.model_validate_json(b'{\"ms\": \"180\"}'))")
    return {"lax_string_for_integer": run([PY, "-c", code], HERE).strip()}


MSGSPEC_UNION = r"""
import msgspec
from typing import Literal, Union
class LookAt(msgspec.Struct): x: float; y: float; z: float
class LookIdle(msgspec.Struct): mode: Literal["idle"]
try:
    msgspec.json.decode(b'{"mode": "idle"}', type=Union[LookAt, LookIdle])
    print("untagged union: decoded")
except TypeError as err:
    print(f"untagged union: refused: {err}")
class Tagged(msgspec.Struct, tag=True): x: float; y: float; z: float
print("tagged struct puts on the wire:", msgspec.json.encode(Tagged(1.2, 3.5, 1.0)).decode())
"""


def msgspec_union() -> list[str]:
    """Can msgspec read 'LookAt or LookIdle' in one step, keeping the ICD's JSON?"""
    return run([PY, "-c", MSGSPEC_UNION], HERE).splitlines()


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    results = {
        "machine": {"python": platform.python_version(), "platform": platform.platform(),
                    "cpu": platform.processor() or platform.machine()},
        "versions": json.loads(run([PY, "-c", "import json, pydantic, pydantic_core, msgspec; print(json.dumps("
                                        "{'pydantic': pydantic.VERSION, 'pydantic_core': pydantic_core.__version__,"
                                        " 'msgspec': msgspec.__version__}))"], HERE)),
        "probes": probes(),
        "sample_change": sample_change(),
        "footprint": footprint(),
        "install_size_mb": install_size(),
        "code_lines": code_lines(),
        "pydantic_default_mode": pydantic_default_mode(),
        "msgspec_union": msgspec_union(),
    }
    (OUT / "results.json").write_text(json.dumps(results, indent=1) + "\n")
    for opt, r in results["probes"].items():
        (OUT / f"logs/probe-{opt}.json").write_text(json.dumps(r, indent=1) + "\n")
    print(json.dumps({k: results[k] for k in ("sample_change", "footprint", "install_size_mb", "code_lines",
                                              "pydantic_default_mode", "msgspec_union")}, indent=1))
