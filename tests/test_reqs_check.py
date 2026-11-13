"""Tests for the requirements checker (tools/reqs).

Most tests build a tiny, valid baseline in a temporary folder, break one thing, and
check the checker notices. The first six are the seeded-error classes from the TS-001
trial (docs/trades/results/TS-001/README.md, gate G2). The last tests run the checker on
the real repository.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import yaml

from tools.reqs.check import main
from tools.reqs.checks import check_all
from tools.reqs.load import TRACE, load
from tools.reqs.schema import problems
from tools.reqs.trace import render

REPO_ROOT = Path(__file__).resolve().parent.parent

SPEC_TREE = """\
# Spec tree (test)

Components: `monster-brain`, `eye-renderer`, `desktop`.

```yaml
spec_tree:
  system: {prefix: SYS, name: Test system}
  subsystems:
    - {prefix: EYE, name: Eyes, group: delivered}
    - {prefix: SHW, name: Show control, group: delivered}
    - {prefix: DEV, name: Desktop tooling, group: enabling, requirements: none}
  externals: [owner-phone]
```
"""

SYSTEM = [
    {"id": "SYS-001", "text": "The monster shall look at visitors.", "type": "functional",
     "verify": "demonstration", "decomposition": "Brain sends a point; eye aims.", "source": "test",
     "stage": 0, "status": "proposed"},
]
EYE = [
    {"id": "EYE-001", "text": "The eye shall turn toward the look point.", "type": "functional",
     "derives_from": ["SYS-001"], "allocated_to": "eye-renderer", "allocation_rationale": "Draws the eye.",
     "verify": "test", "source": "test", "stage": 0, "status": "proposed"},
    {"id": "EYE-002", "text": "The eye shall accept look points per ICD-001.", "type": "interface",
     "derives_from": ["SYS-001"], "allocated_to": "eye-renderer", "allocation_rationale": "Eye end of ICD-001.",
     "icd": "ICD-001", "verify": "test", "source": "test", "stage": 0, "status": "proposed"},
]
SHW = [
    {"id": "SHW-001", "text": "The brain shall publish look points per ICD-001.", "type": "interface",
     "derives_from": ["SYS-001"], "allocated_to": "monster-brain", "allocation_rationale": "Brain end of ICD-001.",
     "icd": "ICD-001", "verify": "test", "source": "test", "stage": 0, "status": "proposed"},
]
COMPONENTS = [
    {"id": "monster-brain", "kind": "software", "subsystem": "SHW", "name": "Brain", "stage": 0,
     "deployed_on": {0: "desktop"}},
    {"id": "eye-renderer", "kind": "software", "subsystem": "EYE", "name": "Eye", "stage": 0,
     "deployed_on": {0: "desktop"}},
    {"id": "desktop", "kind": "part", "subsystem": "DEV", "name": "Desktop", "stage": 0},
]
ICD = """\
# ICD-001 — Look points

```yaml
id: ICD-001
title: Look points
status: draft
ends:
  - {component: monster-brain}
  - {component: eye-renderer}
medium: MQTT
messages:
  - name: look
    topic: test/eyes/look
    from: monster-brain
    to: eye-renderer
    payload_schema:
      type: object
      required: [x, y, z]
      properties: {x: {type: number}, y: {type: number}, z: {type: number}}
    examples:
      - {x: 1.2, y: 3.5, z: 1.0}
```
"""
TBD = """\
| ID | What | Resolved by | Blocks | Needed by | Status |
|---|---|---|---|---|---|
| TBD-001 | Something open | Owner decision | — | — | Open |
"""
TOPICS = '''\
EYES_LOOK = "test/eyes/look"


def is_pattern(topic):
    return "+" in topic or "#" in topic
'''


def write_baseline(root: Path, system=None, eye=None, shw=None, icd=ICD, topics=TOPICS,
                   components=None, pages=True) -> Path:
    """A small, valid baseline under root. Pass a list or text to replace one part."""
    req = root / "docs/requirements"
    req.mkdir(parents=True)
    (root / "docs/architecture").mkdir()
    (root / "docs/interfaces").mkdir()
    (root / "shared").mkdir()
    (req / "spec-tree.md").write_text(SPEC_TREE)
    (req / "system.yaml").write_text(yaml.safe_dump(system if system is not None else SYSTEM, sort_keys=False))
    (req / "eye.yaml").write_text(yaml.safe_dump(eye if eye is not None else EYE, sort_keys=False))
    (req / "shw.yaml").write_text(yaml.safe_dump(shw if shw is not None else SHW, sort_keys=False))
    comps = components if components is not None else COMPONENTS
    (root / "docs/architecture/components.yaml").write_text(yaml.safe_dump(comps, sort_keys=False))
    if pages:
        for folder, cid in (("software", "monster-brain"), ("software", "eye-renderer"), ("nodes", "desktop")):
            (root / f"docs/architecture/{folder}").mkdir(exist_ok=True)
            (root / f"docs/architecture/{folder}/{cid}.md").write_text(f"# {cid}\n")
    (root / "docs/interfaces/ICD-001-look.md").write_text(icd)
    (root / "docs/TBD.md").write_text(TBD)
    (root / "shared/topics.py").write_text(topics)
    return root


def findings(root: Path, level: str = "error") -> list[str]:
    return [str(f) for f in check_all(load(root)) if f.level == level]


def changed(reqs: list[dict], rid: str, **fields) -> list[dict]:
    """A copy of reqs with one requirement's fields changed (None removes a field)."""
    out = []
    for r in reqs:
        r = dict(r)
        if r["id"] == rid:
            for k, v in fields.items():
                if v is None:
                    r.pop(k, None)
                else:
                    r[k] = v
        out.append(r)
    return out


def test_clean_baseline_has_no_findings(tmp_path):
    root = write_baseline(tmp_path)
    assert [str(f) for f in check_all(load(root))] == []
    assert main(["--root", str(root)]) == 0
    assert (root / TRACE).exists()


# ── The six seeded-error classes from TS-001 (gate G2) ──────────────────────────

def test_seeded_1_parent_does_not_exist(tmp_path):
    root = write_baseline(tmp_path, eye=changed(EYE, "EYE-001", derives_from=["SYS-099"]))
    assert any("parent SYS-099 does not exist" in e for e in findings(root))


def test_seeded_2_orphan_without_parent(tmp_path):
    root = write_baseline(tmp_path, eye=changed(EYE, "EYE-001", derives_from=None))
    assert any("EYE-001" in e and "orphan" in e for e in findings(root))


def test_seeded_3_bad_type(tmp_path):
    root = write_baseline(tmp_path, eye=changed(EYE, "EYE-001", type="functionality"))
    assert any("type must be one of" in e for e in findings(root))


def test_seeded_4_unallocated(tmp_path):
    root = write_baseline(tmp_path, eye=changed(EYE, "EYE-001", allocated_to=None))
    assert any("EYE-001" in e and "not allocated" in e for e in findings(root))


def test_seeded_5_interface_without_icd(tmp_path):
    root = write_baseline(tmp_path, eye=changed(EYE, "EYE-002", icd=None))
    assert any("EYE-002" in e and "no icd" in e for e in findings(root))
    root2 = write_baseline(tmp_path / "b", eye=changed(EYE, "EYE-002", icd="ICD-099"))
    assert any("ICD-099 does not exist" in e for e in findings(root2))


def test_seeded_6_unknown_tbd(tmp_path):
    root = write_baseline(tmp_path, eye=changed(EYE, "EYE-001", text="The eye shall settle within TBD-042."))
    assert any("TBD-042 is not in the TBD register" in e for e in findings(root))


def test_checker_exits_nonzero_on_an_error(tmp_path):
    root = write_baseline(tmp_path, eye=changed(EYE, "EYE-001", type="functionality"))
    assert main(["--root", str(root), "--no-write"]) == 1


# ── Spec tree and allocation ────────────────────────────────────────────────────

def test_prefix_must_be_in_spec_tree(tmp_path):
    root = write_baseline(tmp_path, eye=EYE + [dict(EYE[0], id="ZZZ-001")])
    assert any("prefix ZZZ is not a subsystem" in e for e in findings(root))


def test_requirement_must_be_in_its_prefix_file(tmp_path):
    root = write_baseline(tmp_path, eye=EYE + [dict(SHW[0], id="SHW-002")])
    assert any("belongs in shw.yaml, not eye.yaml" in e for e in findings(root))


def test_allocation_must_stay_in_subsystem_unless_explained(tmp_path):
    root = write_baseline(tmp_path, eye=changed(EYE, "EYE-001", allocated_to="monster-brain"))
    assert any("which belongs to SHW, not EYE" in e for e in findings(root))
    explained = changed(EYE, "EYE-001", allocated_to="monster-brain", allocation_note="test reason")
    root2 = write_baseline(tmp_path / "b", eye=explained)
    assert findings(root2) == []


def test_system_requirement_may_not_have_parent_or_allocation(tmp_path):
    root = write_baseline(tmp_path, system=changed(SYSTEM, "SYS-001", allocated_to="eye-renderer"))
    assert any("allocated through their children" in e for e in findings(root))


def test_misspelled_field_is_an_error(tmp_path):
    root = write_baseline(tmp_path, eye=changed(EYE, "EYE-001", derived_from=["SYS-001"]))
    assert any("unknown field 'derived_from'" in e for e in findings(root))


def test_duplicate_id_is_an_error(tmp_path):
    root = write_baseline(tmp_path, eye=EYE + [EYE[0]])
    assert any("EYE-001 is also defined" in e for e in findings(root))


def test_derives_from_loop_is_an_error(tmp_path):
    eye = changed(EYE, "EYE-001", derives_from=["EYE-002"])
    eye = changed(eye, "EYE-002", derives_from=["EYE-001"])
    root = write_baseline(tmp_path, eye=eye)
    assert any("its own ancestor" in e for e in findings(root))


def test_bare_tbd_is_an_error(tmp_path):
    root = write_baseline(tmp_path, eye=changed(EYE, "EYE-001", text="The eye shall settle within TBD ms."))
    assert any("bare 'TBD'" in e for e in findings(root))


# ── ICDs, topics and coverage ───────────────────────────────────────────────────

def test_icd_example_must_match_schema(tmp_path):
    root = write_baseline(tmp_path, icd=ICD.replace("{x: 1.2, y: 3.5, z: 1.0}", "{x: 1.2, y: 3.5}"))
    assert any("missing required key 'z'" in e for e in findings(root))


def test_icd_end_must_be_a_component(tmp_path):
    root = write_baseline(tmp_path, icd=ICD.replace("{component: eye-renderer}", "{component: eye-thing}"))
    assert any("end eye-thing is not in" in e for e in findings(root))


def test_topic_mismatches_are_warnings_both_ways(tmp_path):
    topics = TOPICS + 'EYES_BLINK = "test/eyes/blink"\n'
    icd = ICD.replace("topic: test/eyes/look", "topic: test/eyes/gaze")
    root = write_baseline(tmp_path, icd=icd, topics=topics)
    warnings = findings(root, "warning")
    assert any("test/eyes/gaze is in the ICD but not in shared/topics.py" in w for w in warnings)
    assert any("EYES_BLINK = test/eyes/blink is in no ICD" in w for w in warnings)
    assert findings(root) == []                                   # warnings alone don't fail...
    assert main(["--root", str(root), "--no-write"]) == 0
    assert main(["--root", str(root), "--no-write", "--strict"]) == 1  # ...unless --strict


def test_topic_placeholders_match_shared_helpers(tmp_path):
    topics = TOPICS + textwrap.dedent('''
        def eye_status(side):
            return f"test/eyes/{side}/status"
        EYES_LEFT_STATUS = eye_status("left")
    ''')
    icd = ICD.replace("    examples:\n      - {x: 1.2, y: 3.5, z: 1.0}\n",
                      "    examples:\n      - {x: 1.2, y: 3.5, z: 1.0}\n"
                      "  - name: status\n    topic: test/eyes/{side}/status\n"
                      "    from: eye-renderer\n    to: monster-brain\n")
    root = write_baseline(tmp_path, icd=icd, topics=topics)
    assert findings(root, "warning") == []


def test_undecomposed_system_requirement_is_a_gap(tmp_path):
    root = write_baseline(tmp_path, system=SYSTEM + [dict(SYSTEM[0], id="SYS-002")])
    assert any("SYS-002" in g and "no children" in g for g in findings(root, "gap"))
    assert findings(root) == []


def test_icd_side_without_interface_requirement_is_a_gap(tmp_path):
    root = write_baseline(tmp_path, shw=changed(SHW, "SHW-001", type="functional", icd=None))
    assert any("ICD-001" in g and "SHW side" in g for g in findings(root, "gap"))


def test_allocation_rationale_is_required(tmp_path):
    root = write_baseline(tmp_path, eye=changed(EYE, "EYE-001", allocation_rationale=None))
    assert any("EYE-001" in e and "missing allocation_rationale" in e for e in findings(root))


def test_decomposition_is_required(tmp_path):
    root = write_baseline(tmp_path, system=changed(SYSTEM, "SYS-001", decomposition=None))
    assert any("SYS-001" in e and "missing decomposition" in e for e in findings(root))


def test_deleted_requirement_needs_no_rationale(tmp_path):
    deleted = dict(EYE[0], id="EYE-003", status="deleted")
    deleted.pop("allocation_rationale")
    root = write_baseline(tmp_path, eye=EYE + [deleted])
    assert findings(root) == []


def test_performance_without_basis_is_a_gap(tmp_path):
    root = write_baseline(tmp_path, eye=changed(EYE, "EYE-001", type="performance"))
    assert any("EYE-001" in g and "not yet backed" in g for g in findings(root, "gap"))
    assert findings(root) == []
    based = changed(EYE, "EYE-001", type="performance", basis={"method": "estimate", "ref": "vendor data"})
    root2 = write_baseline(tmp_path / "b", eye=based)
    assert not any("EYE-001" in g for g in findings(root2, "gap"))


def test_basis_must_be_well_formed(tmp_path):
    root = write_baseline(tmp_path, eye=changed(EYE, "EYE-001", basis={"method": "guess", "ref": "x"}))
    assert any("basis must be" in e for e in findings(root))
    root2 = write_baseline(tmp_path / "b", eye=changed(EYE, "EYE-001", basis={"method": "model", "ref": "tools/none.py"}))
    assert any("basis ref tools/none.py does not exist" in e for e in findings(root2))


def test_interface_requirement_must_be_on_an_icd_end(tmp_path):
    comps = COMPONENTS + [{"id": "eye-helper", "kind": "part", "subsystem": "EYE", "name": "Helper", "stage": 0}]
    root = write_baseline(tmp_path, components=comps, eye=changed(EYE, "EYE-002", allocated_to="eye-helper"))
    assert any("not one of ICD-001's ends" in e for e in findings(root))


def test_allocation_to_twin_parts(tmp_path):
    comps = COMPONENTS + [
        {"id": "pi-left", "kind": "part", "subsystem": "EYE", "name": "Pi L", "stage": 0},
        {"id": "pi-right", "kind": "part", "subsystem": "EYE", "name": "Pi R", "stage": 0},
    ]
    eye = EYE + [dict(EYE[0], id="EYE-003", allocated_to=["pi-left", "pi-right"])]
    root = write_baseline(tmp_path, components=comps, eye=eye)
    spec = (root / "docs/requirements/spec-tree.md")
    spec.write_text(spec.read_text().replace("`desktop`.", "`desktop`, `pi-left`, `pi-right`."))
    assert findings(root) == []
    eye_bad = EYE + [dict(EYE[0], id="EYE-003", allocated_to=["pi-left", "monster-brain"])]
    root2 = write_baseline(tmp_path / "b", components=comps, eye=eye_bad)
    assert any("monster-brain, which belongs to SHW" in e for e in findings(root2))


def test_software_and_hosts_need_pages(tmp_path):
    root = write_baseline(tmp_path, pages=False)
    errors = findings(root)
    assert any("needs a page: docs/architecture/software/eye-renderer.md" in e for e in errors)
    assert any("needs a page: docs/architecture/nodes/desktop.md" in e for e in errors)


def _budget_components(have, renderer_need, os_need=0):
    comps = [dict(c) for c in COMPONENTS]
    for c in comps:
        if c["id"] == "desktop":
            c["provides"] = {"memory_mb": have}
            c["needs"] = {"memory_mb": os_need}
        if c["id"] == "eye-renderer":
            c["needs"] = {"memory_mb": renderer_need}
        if c["id"] == "monster-brain":
            c["needs"] = {"memory_mb": 100}
    return comps


def test_budget_within_capacity_is_clean(tmp_path):
    root = write_baseline(tmp_path, components=_budget_components(1024, 153, os_need=300))
    assert [str(f) for f in check_all(load(root))] == []


def test_budget_over_capacity_is_an_error(tmp_path):
    root = write_baseline(tmp_path, components=_budget_components(512, 153, os_need=300))
    assert any("budget desktop" in e and "needs 553 but has 512" in e for e in findings(root))


def test_budget_with_tbd_is_a_gap(tmp_path):
    tbd = (TBD + "| TBD-002 | Memory | Measurement | — | — | Open |\n")
    root = write_baseline(tmp_path, components=_budget_components(1024, "TBD-002"))
    (root / "docs/TBD.md").write_text(tbd)
    assert any("budget desktop" in g and "waiting for TBD-002" in g for g in findings(root, "gap"))
    assert findings(root) == []


def test_budget_amount_must_be_number_or_tbd(tmp_path):
    root = write_baseline(tmp_path, components=_budget_components(1024, "lots"))
    assert any("must be a number or a TBD-NNN" in e for e in findings(root))


def test_icd_file_examples_are_checked_too(tmp_path):
    icd = ICD.replace("medium: MQTT\n", "medium: MQTT\nfiles:\n  - name: settings\n    path: x.yaml\n"
                      "    payload_schema: {type: object, required: [a]}\n    examples: [{b: 1}]\n")
    root = write_baseline(tmp_path, icd=icd)
    assert any("settings: example" in e and "missing required key 'a'" in e for e in findings(root))


def _events(root, events):
    (root / "docs/requirements/verification.yaml").write_text(yaml.safe_dump(events, sort_keys=False))


GOOD_EVENTS = [
    {"id": "VE-001", "name": "Demo", "stage": 0, "method": "demonstration", "covers": ["SYS-001"]},
    {"id": "VE-002", "name": "Tests", "stage": 0, "method": "test", "covers": ["EYE-001", "EYE-002", "SHW-001"]},
]


def test_verification_plan_covering_everything_is_clean(tmp_path):
    root = write_baseline(tmp_path)
    _events(root, GOOD_EVENTS)
    assert [str(f) for f in check_all(load(root))] == []
    assert "## Verification plan" in render(load(root), [])


def test_verification_file_is_not_read_as_requirements(tmp_path):
    root = write_baseline(tmp_path)
    _events(root, GOOD_EVENTS)
    assert sorted(load(root).reqs) == ["EYE-001", "EYE-002", "SHW-001", "SYS-001"]


def test_requirement_without_an_event_is_a_gap(tmp_path):
    root = write_baseline(tmp_path)
    _events(root, GOOD_EVENTS[:1])
    gaps = findings(root, "gap")
    assert any("EYE-001" in g and "no verification event by test" in g for g in gaps)
    assert findings(root) == []


def test_event_method_must_match_the_requirement(tmp_path):
    root = write_baseline(tmp_path)
    _events(root, [dict(GOOD_EVENTS[0], covers=["SYS-001", "EYE-001"]), GOOD_EVENTS[1]])
    assert any("covers EYE-001, which is verified by test, but this event is a demonstration" in e
               for e in findings(root))


def test_event_errors(tmp_path):
    root = write_baseline(tmp_path)
    _events(root, GOOD_EVENTS + [{"id": "VE-9", "name": "x", "stage": 7, "method": "guess",
                                  "covers": ["SYS-404"], "colour": "red"}])
    errors = findings(root)
    for expected in ("must look like VE-001", "stage must be", "method must be", "SYS-404, which does not exist",
                     "unknown field 'colour'"):
        assert any(expected in e for e in errors), expected


def test_schema_subset():
    s = {"type": "object", "required": ["name"], "additionalProperties": False,
         "properties": {"name": {"enum": ["happy", "sleepy"]}, "ms": {"type": "integer", "minimum": 0}}}
    assert problems({"name": "happy", "ms": 300}, s) == []
    assert problems({"name": "angry"}, s)
    assert problems({"name": "happy", "ms": -1}, s)
    assert problems({"name": "happy", "colour": 1}, s)
    assert problems({"name": "happy"}, {"type": "object", "patternProperties": {}})  # unsupported keyword


# ── The real repository ─────────────────────────────────────────────────────────

def test_repository_baseline_has_no_errors():
    errors = [str(f) for f in check_all(load(REPO_ROOT)) if f.level == "error"]
    assert errors == []


def test_trace_md_is_up_to_date():
    model = load(REPO_ROOT)
    expected = render(model, check_all(model))
    actual = (REPO_ROOT / TRACE).read_text()
    assert actual == expected, "docs/requirements/trace.md is stale: run .venv/bin/python -m tools.reqs.check"


def test_impact_query_runs():
    assert main(["--impact", "SYS-001"]) == 0
    assert main(["--impact", "SYS-999"]) == 1
