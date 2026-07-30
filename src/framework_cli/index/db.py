from __future__ import annotations

import sqlite3
from pathlib import Path

from .schema import SCHEMA, SCHEMA_VERSION


class IndexDB:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)
        self.connection.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES('schema_version',?)", (str(SCHEMA_VERSION),))
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def execute(self, sql: str, params: tuple = ()):
        cur = self.connection.execute(sql, params)
        self.connection.commit()
        return cur
