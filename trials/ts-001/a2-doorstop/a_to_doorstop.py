"""Convert TS-001 option A requirements YAML into Doorstop items (conversion-cost evidence)."""
import sys, pathlib, yaml
a, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
folder = {"SYS": "sys", "BRN": "brn", "EYE": "eye"}
for f in sorted((a / "requirements").glob("*.yaml")):
    for r in yaml.safe_load(f.read_text()):
        item = {"active": True, "derived": False, "header": "", "level": float(r["id"][-1]),
                "links": [{p: None} for p in r.get("derives_from", [])],
                "normative": True, "ref": "", "reviewed": None, "text": r["text"] + "\n",
                "type": r["type"], "verify": r["verify"]}
        for k in ("allocated_to", "icd", "rationale"):
            if k in r: item[k] = r[k]
        (out / folder[r["id"][:3]] / f"{r['id']}.yml").write_text(yaml.safe_dump(item, sort_keys=False, allow_unicode=True))
