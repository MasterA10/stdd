from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json


REWORK_LINE_THRESHOLD = 500


@dataclass
class RunResult:
    run_id: str
    command: list[str]
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    changed_files: list[str] = field(default_factory=list)
    status: str = "passed"

    def to_dict(self) -> dict[str, Any]:
        """Converte o objeto RunResult para um dicionário serializável.
        Aplica a função asdict da dataclass no próprio objeto.
        """
        return asdict(self)

    def write(self, directory: Path) -> None:
        """Grava os relatórios e logs do resultado no diretório informado.
        Cria a pasta e salva os arquivos result.json, stdout.log e stderr.log.
        """
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "result.json").write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (directory / "stdout.log").write_text(self.stdout, encoding="utf-8")
        (directory / "stderr.log").write_text(self.stderr, encoding="utf-8")


@dataclass
class RunDiffSnapshot:
    run_id: str
    timestamp: str
    files: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Converte o snapshot detalhado de código para um dicionário serializável.
        Aplica a função asdict da dataclass no objeto de snapshot.
        """
        return asdict(self)


@dataclass
class RunLogEntry:
    run_id: str
    timestamp: str
    description: str
    work_types: list[str]
    diff_stats: dict[str, Any] = field(default_factory=dict)
    detailed_files: list[dict[str, Any]] = field(default_factory=list)
    workspace_snapshot: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Converte a entrada de registro para um dicionário serializável.
        Chama a função asdict da dataclass no objeto atual.
        """
        data = asdict(self)
        data.pop("detailed_files", None)
        data.pop("workspace_snapshot", None)
        return data

    def write(self, directory: Path) -> Path:
        """Acumula a execução no summary e no snapshot únicos da pasta do dia.
        Mantém cada run_id e seus detalhes em ordem de gravação, sem criar arquivos por execução.
        """
        try:
            dt = datetime.fromisoformat(self.timestamp)
        except (ValueError, TypeError):
            dt = datetime.now(timezone.utc)

        date_folder = dt.strftime("%Y-%m-%d")
        day_dir = directory / date_folder
        day_dir.mkdir(parents=True, exist_ok=True)

        summary_file = day_dir / f"{date_folder}_summary.json"
        self._remove_legacy_daily_files(day_dir, summary_file, f"{date_folder}_snapshot.json")
        summary_data = self._read_daily_document(summary_file, date_folder, "runs")
        self._mark_large_runs_as_refactor(summary_data["runs"])
        summary_data["runs"].append(self.to_dict())
        summary_data["run_count"] = len(summary_data["runs"])
        summary_data["last_run_id"] = self.run_id
        summary_file.write_text(
            json.dumps(summary_data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        snapshot_file = day_dir / f"{date_folder}_snapshot.json"
        snapshot_data = self._read_daily_document(snapshot_file, date_folder, "runs")
        snapshot_data["runs"].append(
            RunDiffSnapshot(
                run_id=self.run_id,
                timestamp=self.timestamp,
                files=self.detailed_files,
            ).to_dict()
        )
        snapshot_data["run_count"] = len(snapshot_data["runs"])
        snapshot_data["last_run_id"] = self.run_id
        snapshot_data["workspace_snapshot"] = self.workspace_snapshot
        snapshot_file.write_text(
            json.dumps(snapshot_data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        return summary_file

    @staticmethod
    def _read_daily_document(path: Path, date_folder: str, collection_key: str) -> dict[str, Any]:
        """Lê o documento diário acumulativo ou cria sua estrutura inicial.
        Descarta conteúdo inválido para permitir que uma nova execução regenere o relatório com segurança.
        """
        if path.exists():
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(document, dict) and isinstance(document.get(collection_key), list):
                    return document
                if isinstance(document, dict) and document.get("run_id"):
                    legacy_entry = dict(document)
                    legacy_entry.pop("version", None)
                    legacy_entry.pop("date", None)
                    return {"version": 1, "date": date_folder, collection_key: [legacy_entry]}
            except (OSError, json.JSONDecodeError):
                pass
        return {"version": 1, "date": date_folder, collection_key: []}

    @staticmethod
    def _mark_large_runs_as_refactor(runs: list[dict[str, Any]]) -> None:
        """Completa registros antigos com refactor quando representam retrabalho grande.
        Preserva a primeira captura do histórico e classifica somente mudanças posteriores extensas.
        """
        for run in runs[1:]:
            stats = run.get("diff_stats", {})
            lines_added = int(stats.get("lines_added", 0))
            lines_deleted = int(stats.get("lines_deleted", 0))
            work_types = run.get("work_types", [])
            if lines_added >= REWORK_LINE_THRESHOLD and lines_deleted >= REWORK_LINE_THRESHOLD and isinstance(work_types, list) and "refactor" not in work_types:
                work_types.append("refactor")

    @staticmethod
    def _remove_legacy_daily_files(day_dir: Path, summary_file: Path, snapshot_name: str) -> None:
        """Remove arquivos antigos com timestamp da pasta diária antes de atualizar o par canônico.
        Limita a limpeza aos nomes de summary e snapshot e preserva os arquivos fixos do dia.
        """
        for pattern, current_name in (("*_summary.json", summary_file.name), ("*_snapshot.json", snapshot_name)):
            for candidate in day_dir.glob(pattern):
                if candidate.name != current_name:
                    candidate.unlink()
