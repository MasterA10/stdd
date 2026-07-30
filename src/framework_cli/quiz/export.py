from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..reporting.models import CommandResult
from .repository import QuizRepository


def export_quiz(root: Path, fmt: str = "json") -> CommandResult:
    from ..learn.store import LearnStore
    store = LearnStore(root); result = CommandResult("framework quiz export", metadata={"enabled": store.enabled()})
    if not store.enabled(): result.status = "disabled"; return result
    questions = QuizRepository(store).questions()
    output = store.base / "quiz" / f"questions.{fmt}"
    if fmt == "json": output.write_text(json.dumps(questions, indent=2, ensure_ascii=False) + "\n")
    elif fmt == "yaml":
        try:
            import yaml; output.write_text(yaml.safe_dump(questions, sort_keys=False))
        except ImportError: output.write_text(json.dumps(questions, indent=2) + "\n")
    elif fmt == "markdown":
        lines = ["# Codebase Quiz", ""]
        for index, q in enumerate(questions, 1): lines.extend([f"## {index}. {q.get('prompt', '')}", "", *[f"- {x}" for x in q.get("options", [])], ""])
        output.write_text("\n".join(lines))
    else:
        result.status, result.exit_code = "error", 2; result.actions.append("Format must be json, yaml or markdown"); return result
    result.metadata["path"] = str(output.relative_to(store.root)); result.metadata["count"] = len(questions)
    return result
