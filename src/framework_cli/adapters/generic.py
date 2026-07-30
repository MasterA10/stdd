from __future__ import annotations

import json
from pathlib import Path

from .base import BaseAdapter, Detection


class GenericAdapter(BaseAdapter):
    id = "generic"

    def detect(self, root: Path) -> list[Detection]:
        results: list[Detection] = []
        if (root / "Dockerfile").exists() or list(root.glob("Dockerfile.*")):
            results.append(Detection("infrastructure", "docker", .99, ["Dockerfile"]))
        if (root / "docker-compose.yml").exists() or (root / "docker-compose.yaml").exists():
            results.append(Detection("infrastructure", "docker-compose", .99, ["docker-compose.yml"]))
        for name in (".env", ".env.example", ".env.sample"):
            if (root / name).exists():
                results.append(Detection("configuration", name, .99, [name]))
        return results
