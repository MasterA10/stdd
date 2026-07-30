from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..learn.cli_adapters import execute_command
from ..learn.redaction import redact_record
from ..learn.store import write_json


def generate_with_command(store, target: str, request: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    clean, _ = redact_record(request)
    path = store.base / "quiz" / "requests" / f"{request['job_id']}.json"
    write_json(store, path, clean)
    return execute_command(store.root, target, path)
