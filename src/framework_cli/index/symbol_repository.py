from __future__ import annotations

import json
from typing import Any

from .db import IndexDB


class SymbolRepository:
    """Persistence boundary for the source symbol catalog and its relations."""

    def __init__(self, db: IndexDB):
        self.db = db

    def clear(self) -> None:
        self.db.execute("DELETE FROM symbol_relations")
        self.db.execute("DELETE FROM symbols")

    def save(self, data: dict[str, Any]) -> None:
        self.db.execute("INSERT OR REPLACE INTO symbols VALUES (?,?,?,?,?,?,?,?,?)", (
            data["id"], data["path"], data["name"], data["kind"], data.get("line"),
            data.get("end_line"), data.get("signature", ""), data["fingerprint"],
            json.dumps(data, sort_keys=True)))

    def relation(self, data: dict[str, Any]) -> None:
        self.db.execute("INSERT OR REPLACE INTO symbol_relations VALUES (?,?,?,?,?)", (
            data["source_id"], data["target_id"], data["relation"],
            data["fingerprint"], json.dumps(data, sort_keys=True)))
