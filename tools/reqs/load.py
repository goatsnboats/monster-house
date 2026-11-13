"""Read the requirements baseline from the repository into plain Python data.

Nothing here judges the content; checks.py does that. Problems that stop a file
from being read at all (bad YAML, a duplicate ID) are collected in
`Model.load_errors` so the checker can report them with everything else.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Where everything lives, relative to the repository root.
REQ_DIR = "docs/requirements"
SPEC_TREE = "docs/requirements/spec-tree.md"
TRACE = "docs/requirements/trace.md"
VERIFICATION = "docs/requirements/verification.yaml"
RISKS = "docs/requirements/risks.yaml"
# YAML files in REQ_DIR that are not requirements.
NOT_REQUIREMENTS = {"verification.yaml", "risks.yaml"}
ARCH_DIR = "docs/architecture"
COMPONENTS = "docs/architecture/components.yaml"
ICD_DIR = "docs/interfaces"
TBD_FILE = "docs/TBD.md"
TOPICS_FILE = "shared/topics.py"

YAML_BLOCK = re.compile(r"```yaml\n(.*?)```", re.S)
TBD_ROW = re.compile(r"^\|\s*(TBD-\d{3})\s*\|", re.M)


@dataclass
class Model:
    """Everything the checker looks at, keyed by ID."""

    root: Path
    prefixes: dict[str, dict] = field(default_factory=dict)  # "EYE" -> {name, group}; includes "SYS"
    externals: set[str] = field(default_factory=set)         # house, owner-phone, ...
    reqs: dict[str, dict] = field(default_factory=dict)      # "EYE-001" -> requirement
    comps: dict[str, dict] = field(default_factory=dict)     # "eye-renderer" -> component
    icds: dict[str, dict] = field(default_factory=dict)      # "ICD-001" -> structured block
    events: dict[str, dict] = field(default_factory=dict)    # "VE-001" -> verification event
    tbds: set[str] = field(default_factory=set)              # IDs in the TBD register
    spec_tree_text: str = ""
    load_errors: list[tuple[str, str]] = field(default_factory=list)  # (where, message)

    def subsystem_of(self, req_id: str) -> str:
        """The prefix of a requirement ID: subsystem_of("EYE-012") -> "EYE"."""
        return req_id.split("-")[0]


def load(root: Path) -> Model:
    model = Model(root=root)
    _load_spec_tree(model)
    _load_requirements(model)
    _load_components(model)
    _load_icds(model)
    _load_events(model)
    tbd_path = root / TBD_FILE
    if tbd_path.exists():
        model.tbds = set(TBD_ROW.findall(tbd_path.read_text()))
    else:
        model.load_errors.append((TBD_FILE, "TBD register not found"))
    return model


def yaml_blocks(text: str) -> list[str]:
    """The contents of every ```yaml fenced block in a Markdown text."""
    return YAML_BLOCK.findall(text)


def _read_yaml(model: Model, path: Path, text: str | None = None):
    where = str(path.relative_to(model.root))
    try:
        return yaml.safe_load(text if text is not None else path.read_text())
    except yaml.YAMLError as err:
        model.load_errors.append((where, f"not valid YAML: {err}"))
        return None


def _load_spec_tree(model: Model) -> None:
    path = model.root / SPEC_TREE
    if not path.exists():
        model.load_errors.append((SPEC_TREE, "spec tree not found"))
        return
    model.spec_tree_text = path.read_text()
    for block in yaml_blocks(model.spec_tree_text):
        data = _read_yaml(model, path, block)
        if isinstance(data, dict) and "spec_tree" in data:
            tree = data["spec_tree"]
            system = tree.get("system", {})
            model.prefixes[system.get("prefix", "SYS")] = {"name": system.get("name", ""), "group": "system"}
            for sub in tree.get("subsystems", []):
                model.prefixes[sub["prefix"]] = {"name": sub.get("name", ""), "group": sub.get("group", ""),
                                                 "requirements": sub.get("requirements", "yes")}
            model.externals = set(tree.get("externals", []))
            return
    model.load_errors.append((SPEC_TREE, "no ```yaml block with a spec_tree: key"))


def _load_requirements(model: Model) -> None:
    for path in sorted((model.root / REQ_DIR).glob("*.yaml")):
        if path.name in NOT_REQUIREMENTS:
            continue
        data = _read_yaml(model, path)
        if data is None:
            continue
        if not isinstance(data, list):
            model.load_errors.append((path.name, "must be a YAML list of requirements (or [])"))
            continue
        for req in data:
            if not isinstance(req, dict) or "id" not in req:
                model.load_errors.append((path.name, f"entry without an id: {req!r:.80}"))
                continue
            req["_file"] = path.name
            if req["id"] in model.reqs:
                other = model.reqs[req["id"]]["_file"]
                model.load_errors.append((path.name, f"{req['id']} is also defined in {other} (IDs must be unique)"))
                continue
            model.reqs[req["id"]] = req


def _load_components(model: Model) -> None:
    path = model.root / COMPONENTS
    if not path.exists():
        model.load_errors.append((COMPONENTS, "components file not found"))
        return
    data = _read_yaml(model, path) or []
    for comp in data:
        if not isinstance(comp, dict) or "id" not in comp:
            model.load_errors.append((COMPONENTS, f"entry without an id: {comp!r:.80}"))
            continue
        if comp["id"] in model.comps:
            model.load_errors.append((COMPONENTS, f"component {comp['id']} is listed twice"))
            continue
        model.comps[comp["id"]] = comp


def _load_icds(model: Model) -> None:
    for path in sorted((model.root / ICD_DIR).glob("ICD-*.md")):
        text = path.read_text()
        block = None
        for raw in yaml_blocks(text):
            data = _read_yaml(model, path, raw)
            if isinstance(data, dict) and "id" in data:
                block = data
                break
        if block is None:
            model.load_errors.append((path.name, "no ```yaml block with an id: key"))
            continue
        block["_file"] = path.name
        if block["id"] in model.icds:
            model.load_errors.append((path.name, f"{block['id']} is also defined in {model.icds[block['id']]['_file']}"))
            continue
        model.icds[block["id"]] = block


def _load_events(model: Model) -> None:
    """The verification plan, if there is one yet."""
    path = model.root / VERIFICATION
    if not path.exists():
        return
    data = _read_yaml(model, path)
    if data is None:
        return
    if not isinstance(data, list):
        model.load_errors.append((VERIFICATION, "must be a YAML list of verification events"))
        return
    for event in data:
        if not isinstance(event, dict) or "id" not in event:
            model.load_errors.append((VERIFICATION, f"entry without an id: {event!r:.80}"))
            continue
        if event["id"] in model.events:
            model.load_errors.append((VERIFICATION, f"{event['id']} is listed twice"))
            continue
        model.events[event["id"]] = event
