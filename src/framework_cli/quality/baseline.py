from __future__ import annotations

import json
from pathlib import Path


def load_baseline(path: Path) -> set[str]:
    if not path.exists(): return set()
    try: data = json.loads(path.read_text())
    except (OSError, ValueError): return set()
    return {x.get("fingerprint") for x in data.get("findings", []) if x.get("fingerprint")}


def save_baseline(path: Path, findings: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": 1, "findings": [{"fingerprint": f.get("fingerprint"), "rule": f.get("rule"), "path": f.get("path"), "justification": "legacy baseline", "review": "next quality review"} for f in findings]}, indent=2))
