"""Re-run every TS-001 check and save the logs as evidence.

Usage (from the repo root, with the trial virtual environment that has
strictdoc==0.30.4, doorstop==3.2 and pyyaml installed):

    <venv>/bin/python trials/ts-001/run_checks.py OUT_DIR

Writes OUT_DIR/logs/*.txt, OUT_DIR/seeded-errors.json and the tools' HTML exports
(OUT_DIR/html/...). Every seeded error is planted in a scratch copy under
OUT_DIR/work, never in the trial files themselves.

The SysML v2 validator (sysml_check.sh) isn't run here. It needs the OMG pilot jar,
which isn't in the repo.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BIN = Path(sys.executable).parent
TBD = REPO / "docs" / "TBD.md"

ERRORS = [
    ("parent_missing", "A parent that doesn't exist"),
    ("orphan", "A subsystem requirement with no parent"),
    ("bad_type", "A misspelled requirement type"),
    ("unallocated", "A subsystem requirement allocated to no component"),
    ("interface_no_icd", "An interface requirement with no ICD"),
    ("unknown_tbd", "A TBD ID that isn't in the register"),
]

# Each mutation: list of (relative file, regex, replacement), applied once.
YAML_MUT = {
    "parent_missing": [("requirements/eyes.yaml", r"derives_from: \[SYS-002\]", "derives_from: [SYS-009]")],
    "orphan": [("requirements/brain.yaml", r"  derives_from: \[SYS-001\]\n(  allocated_to: monster-brain\n  verify: test\n\n- id: BRN-002)", r"\1")],
    "bad_type": [("requirements/eyes.yaml", r"type: constraint", "type: constrant")],
    "unallocated": [("requirements/brain.yaml", r"  allocated_to: monster-brain\n", "")],
    "interface_no_icd": [("requirements/brain.yaml", r"  icd: ICD-001\n", "")],
    "unknown_tbd": [("requirements/eyes.yaml", r"within 300 ms\.", "within 300 ms. TBD-999")],
}
SDOC_MUT = {
    "parent_missing": [("requirements.sdoc", r"  VALUE: SYS-002", "  VALUE: SYS-009")],
    "orphan": [("requirements.sdoc", r"(ALLOCATED_TO: monster-brain\nVERIFY: Test\n)RELATIONS:\n- TYPE: Parent\n  VALUE: SYS-001\n", r"\1")],
    "bad_type": [("requirements.sdoc", r"TYPE: Constraint", "TYPE: Constrant")],
    "unallocated": [("requirements.sdoc", r"ALLOCATED_TO: monster-brain\n", "")],
    "interface_no_icd": [("requirements.sdoc", r"ICD: ICD-001\n", "")],
    "unknown_tbd": [("requirements.sdoc", r"within 300 ms\.", "within 300 ms. TBD-999")],
}
DOORSTOP_MUT = {
    "parent_missing": [("eye/EYE-002.yml", r"^- SYS-002:", "- SYS-009:")],
    "orphan": [("brn/BRN-001.yml", r"links:\n- SYS-001:.*\n", "links: []\n")],
    "bad_type": [("eye/EYE-004.yml", r"type: constraint", "type: constrant")],
    "unallocated": [("brn/BRN-001.yml", r"allocated_to: monster-brain\n", "")],
    "interface_no_icd": [("brn/BRN-003.yml", r"icd: ICD-001\n", "")],
    "unknown_tbd": [("eye/EYE-002.yml", r"within 300 ms\.", "within 300 ms. TBD-999")],
}


def run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=300)
    return p.returncode, (p.stdout + p.stderr)


def mutate(root: Path, muts: list[tuple[str, str, str]]) -> None:
    for rel, pattern, repl in muts:
        f = root / rel
        text, n = re.subn(pattern, repl, f.read_text(), count=1, flags=re.M)
        if n != 1:
            raise SystemExit(f"mutation did not apply: {rel} {pattern!r}")
        f.write_text(text)


def git_init(root: Path) -> None:
    for cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                ["git", "-c", "user.name=trial", "-c", "user.email=trial@localhost", "commit", "-qm", "base"]):
        subprocess.run(cmd, cwd=root, check=True)


def first_error(out: str) -> str:
    for line in out.splitlines():
        if re.search(r"error|warning", line, re.I):
            return re.sub(r"/\S*/work/\S+?/", "", line.strip())[:180]
    return ""


def main() -> int:
    out = Path(sys.argv[1]).resolve()
    logs, work = out / "logs", out / "work"
    shutil.rmtree(work, ignore_errors=True)
    logs.mkdir(parents=True, exist_ok=True)
    py = str(BIN / "python")

    def log(name: str, text: str) -> None:
        (logs / f"{name}.txt").write_text(text)

    # --- Option A: clean run, report, impact ---------------------------------
    rc, o = run([py, str(HERE / "a/check.py"), "a", "--tbd", str(TBD), "--report", str(out / "a-report")], HERE)
    rc2, o2 = run([py, str(HERE / "a/check.py"), "a", "--impact", "SYS-001"], HERE)
    log("a-clean", f"$ python a/check.py a --tbd docs/TBD.md --report a-report\n{o}exit {rc}\n\n"
                   f"$ python a/check.py a --impact SYS-001\n{o2}")

    # --- StrictDoc: clean export + ReqIF ---------------------------------------
    rc, o = run([str(BIN / "strictdoc"), "export", ".", "--output-dir", str(out / "html/strictdoc")], HERE / "b-strictdoc")
    rc2, o2 = run([str(BIN / "strictdoc"), "export", ".", "--formats", "reqif-sdoc", "--output-dir", str(work / "reqif")], HERE / "b-strictdoc")
    reqif = next((work / "reqif").rglob("*.reqif"), None)
    log("b-clean", f"$ strictdoc export . (exit {rc})\n{o[-600:]}\n$ strictdoc export . --formats reqif-sdoc (exit {rc2})\n"
                   f"ReqIF file: {reqif.name if reqif else 'none'} ({reqif.stat().st_size if reqif else 0} bytes)\n")

    # --- Doorstop: publish HTML, and show that validation rewrites files -------
    ds = work / "doorstop-churn"
    shutil.copytree(HERE / "a2-doorstop", ds)
    run([py, str(HERE / "a2-doorstop/a_to_doorstop.py"), str(HERE / "a"), str(ds)], ds)  # fresh items, links unstamped
    git_init(ds)
    rc, o = run([str(BIN / "doorstop")], ds)
    _, status = run(["git", "status", "--short"], ds)
    _, diff = run(["git", "diff", "HEAD", "--stat"], ds)
    _, diff1 = run(["git", "diff", "HEAD", "--", "brn/BRN-002.yml"], ds)
    log("a2-churn", f"$ doorstop            # validate only\n{o}exit {rc}\n\n"
                    f"$ git status --short  # 'M ' in column 1 = staged by doorstop itself\n{status}\n"
                    f"$ git diff HEAD --stat\n{diff}\n$ git diff HEAD -- brn/BRN-002.yml\n{diff1}")
    rc, o = run([str(BIN / "doorstop"), "publish", "all", str(out / "html/doorstop")], ds)
    log("a2-publish", f"$ doorstop publish all html/doorstop\n{o}exit {rc}\n")

    # --- Seeded errors, one at a time -----------------------------------------
    options = {
        "A": dict(src=HERE / "a", muts=YAML_MUT, git=False,
                  cmd=lambda d: [py, str(HERE / "a/check.py"), str(d), "--tbd", str(TBD)]),
        "A′ Doorstop": dict(src=HERE / "a2-doorstop", muts=DOORSTOP_MUT, git=True,
                            cmd=lambda d: [str(BIN / "doorstop"), "--error-all"]),
        "B StrictDoc": dict(src=HERE / "b-strictdoc", muts=SDOC_MUT, git=False,
                            cmd=lambda d: [str(BIN / "strictdoc"), "export", ".", "--output-dir", str(d / "_out")]),
        "D glue": dict(src=HERE / "d-hybrid", muts=YAML_MUT, git=False,
                       cmd=lambda d: [py, str(HERE / "d-hybrid/glue_check.py"), str(d), "--tbd", str(TBD)]),
    }
    results: dict[str, dict] = {}
    for opt, cfg in options.items():
        text = []
        results[opt] = {}
        for key, desc in ERRORS:
            d = work / f"{re.sub(r'[^a-z0-9]+', '-', opt.lower())}-{key}"
            shutil.copytree(cfg["src"], d)
            mutate(d, cfg["muts"][key])
            if cfg["git"]:
                git_init(d)
            rc, o = run(cfg["cmd"](d), d)
            caught = rc != 0
            # Doorstop flags ANY text edit as "unreviewed changes"; that isn't a check for the seeded error.
            incidental = caught and "unreviewed changes" in o and "no item with UID" not in o and "no links to parent" not in o
            if incidental:
                caught = False
            msg = first_error(o) if rc != 0 else ""
            results[opt][key] = {"caught": caught, "incidental": incidental, "exit": rc, "message": msg}
            verdict = "CAUGHT" if caught else ("MISSED (flagged only as an unreviewed text edit)" if incidental else "MISSED")
            text.append(f"--- seeded: {desc} ---\nexit {rc}  →  {verdict}\n" + (msg + "\n" if msg else ""))
        log(f"seeded-{re.sub(r'[^a-z0-9]+', '-', opt.lower()).strip('-')}", "\n".join(text))

    rc, o = run([py, str(HERE / "d-hybrid/glue_check.py"), "d-hybrid", "--tbd", str(TBD)], HERE)
    log("d-clean", f"$ python d-hybrid/glue_check.py d-hybrid --tbd docs/TBD.md\n{o}exit {rc}\n")

    (out / "seeded-errors.json").write_text(json.dumps(
        {"errors": dict(ERRORS), "results": results}, indent=2, ensure_ascii=False))
    for opt, r in results.items():
        print(f"{opt}: {sum(v['caught'] for v in r.values())}/6 caught")
    shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
