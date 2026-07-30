from __future__ import annotations

import json
from typing import Any

from .db import IndexDB


class Repository:
    def __init__(self, db: IndexDB):
        self.db = db

    def project(self, project_id: str, root_path: str, profile: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO projects VALUES (?,?,?)", (project_id, root_path, profile))

    def application(self, app_id: str, project_id: str, path: str, data: dict[str, Any]) -> None:
        self.db.execute("INSERT OR REPLACE INTO applications VALUES (?,?,?,?)", (app_id, project_id, path, json.dumps(data)))

    def finding(self, finding: dict[str, Any]) -> None:
        self.db.execute("INSERT OR REPLACE INTO findings VALUES (?,?,?,?,?)", (finding["id"], finding.get("category", "quality"), finding.get("path"), finding.get("line"), json.dumps(finding)))
