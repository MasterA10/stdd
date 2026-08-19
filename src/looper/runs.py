"""Viewer e índice somente leitura das execuções do Looper."""

import json
from pathlib import Path
from typing import Any


RUNS_TEMPLATE = Path(__file__).parent / "templates" / "runs" / "runs.html"


def runs_directory(root: Path) -> Path:
    """Retorna a pasta que contém os relatórios diários e o índice de runs."""
    return root / ".looper" / "runs"


def ensure_runs_workspace(root: Path) -> list[Path]:
    """Instala o viewer somente leitura e cria o índice vazio de execuções."""
    looper_path = root / ".looper"
    runs_path = runs_directory(root)
    created: list[Path] = []
    runs_path.mkdir(parents=True, exist_ok=True)
    viewer = looper_path / "runs.html"
    template = RUNS_TEMPLATE.read_text(encoding="utf-8")
    if not viewer.exists() or viewer.read_text(encoding="utf-8") != template:
        viewer.write_text(template, encoding="utf-8")
        created.append(viewer)
    index = runs_path / "index.json"
    if not index.exists():
        index.write_text(json.dumps({"version": 1, "days": []}, indent=2) + "\n", encoding="utf-8")
        created.append(index)
    return created


def update_runs_index(root: Path, summary_file: Path) -> Path:
    """Atualiza o índice leve sem duplicar o dia registrado.
    Mantém somente metadados para que o viewer carregue o Summary sob demanda.
    """
    runs_path = runs_directory(root)
    index_path = runs_path / "index.json"
    ensure_runs_workspace(root)
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        index = {"version": 1, "days": []}
    if not isinstance(index, dict) or not isinstance(index.get("days"), list):
        index = {"version": 1, "days": []}
    summary = json.loads(summary_file.read_text(encoding="utf-8"))
    date = summary_file.parent.name
    relative_summary = str(summary_file.relative_to(runs_path))
    relative_snapshot = relative_summary.replace("_summary.json", "_snapshot.json")
    metadata: dict[str, Any] = {
        "date": date,
        "summary": relative_summary,
        "snapshot": relative_snapshot,
        "run_count": summary.get("run_count", len(summary.get("runs", []))),
        "last_run_id": summary.get("last_run_id"),
    }
    days = [item for item in index["days"] if isinstance(item, dict) and item.get("date") != date]
    days.append(metadata)
    days.sort(key=lambda item: str(item.get("date", "")), reverse=True)
    index_path.write_text(json.dumps({"version": 1, "days": days}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return index_path
