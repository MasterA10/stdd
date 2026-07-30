from __future__ import annotations

import json
from pathlib import Path

from .base import BaseAdapter, Detection


class JavaScriptAdapter(BaseAdapter):
    id = "javascript"
    capabilities = {"detection", "tests", "static_rules"}

    def detect(self, root: Path) -> list[Detection]:
        package = root / "package.json"
        if not package.exists():
            return []
        try: data = json.loads(package.read_text())
        except (OSError, ValueError): data = {}
        value = "typescript" if (root / "tsconfig.json").exists() else "javascript"
        results = [Detection("language", value, .99, ["package.json"])]
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        for key, framework in (("react", "react"), ("next", "next"), ("express", "express")):
            if key in deps: results.append(Detection("framework", framework, .95, ["package.json"]))
        return results

    def test_commands(self, root: Path) -> list[list[str]]:
        package = root / "package.json"
        if not package.exists(): return []
        try: scripts = json.loads(package.read_text()).get("scripts", {})
        except (OSError, ValueError): scripts = {}
        return [["npm", "test"]] if "test" in scripts else []
