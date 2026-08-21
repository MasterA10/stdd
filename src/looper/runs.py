"""Viewer e índice somente leitura das execuções do Looper."""

import json
from datetime import datetime, timezone
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
    previous_day = next((item for item in index["days"] if isinstance(item, dict) and item.get("date") == date), {})
    days = [item for item in index["days"] if isinstance(item, dict) and item.get("date") != date]
    if isinstance(previous_day, dict) and previous_day.get("test_report"):
        metadata["test_report"] = previous_day["test_report"]
    days.append(metadata)
    days.sort(key=lambda item: str(item.get("date", "")), reverse=True)
    index_path.write_text(json.dumps({"version": 1, "days": days}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return index_path


def write_test_report(root: Path, report: dict[str, Any]) -> Path:
    """Persiste um resumo visual da última execução do ``looper test``.

    O documento é separado dos logs de trabalho para que o viewer possa explicar
    o resultado sem misturar evidências de testes com diffs de implementação.
    """
    runs_path = runs_directory(root)
    runs_path.mkdir(parents=True, exist_ok=True)
    timestamp = str(report.get("started_at") or datetime.now(timezone.utc).isoformat())
    try:
        date_folder = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).strftime("%Y-%m-%d")
    except ValueError:
        date_folder = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    day_dir = runs_path / date_folder
    day_dir.mkdir(parents=True, exist_ok=True)
    report_path = day_dir / f"{date_folder}_tests.json"
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    static = report.get("static_analysis") if isinstance(report.get("static_analysis"), dict) else {}
    backlog = report.get("backlog") if isinstance(report.get("backlog"), dict) else {}
    human_report = {
        "version": 1,
        "run_id": report.get("run_id"),
        "started_at": timestamp,
        "status": report.get("status"),
        "profile": report.get("profile"),
        "summary": summary,
        "suites": report.get("suites", []),
        "contract": {
            "status": "blocked" if report.get("contract_violations") else "passed",
            "violations": report.get("contract_violations", []),
        },
        "static_analysis": {
            "status": static.get("status"),
            "symbols": static.get("symbols", []),
            "dependencies": static.get("dependencies", []),
            "errors": static.get("errors", []),
            "quality_findings": static.get("quality_findings", []),
        },
        "backlog": {
            "status": backlog.get("status"),
            "remaining": backlog.get("remaining", 0),
            "missing_tests": backlog.get("missing_tests", 0),
        },
    }
    report_path.write_text(json.dumps(human_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    index_path = runs_path / "index.json"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        index = {"version": 1, "days": []}
    if not isinstance(index, dict) or not isinstance(index.get("days"), list):
        index = {"version": 1, "days": []}
    relative_report = str(report_path.relative_to(runs_path))
    days = [day for day in index["days"] if isinstance(day, dict) and day.get("date") != date_folder]
    existing = next((day for day in index["days"] if isinstance(day, dict) and day.get("date") == date_folder), {})
    existing = dict(existing) if isinstance(existing, dict) else {}
    existing.update({"date": date_folder, "test_report": relative_report})
    days.append(existing)
    days.sort(key=lambda day: str(day.get("date", "")), reverse=True)
    index_path.write_text(json.dumps({"version": 1, "days": days}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report_path
