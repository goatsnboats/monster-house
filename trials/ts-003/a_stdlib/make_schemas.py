"""Write schemas.json from the ICDs (in the real thing, the checker does this, like trace.md)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import icd  # noqa: E402

schemas = {name: m["payload_schema"] for name, m in icd.messages().items()}
(Path(__file__).parent / "schemas.json").write_text(json.dumps(schemas, indent=2) + "\n")
