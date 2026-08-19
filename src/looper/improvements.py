"""Persistência das sessões interativas do Draw Improve.

As sessões ficam fora de ``.stdd/draws`` para que respostas humanas possam ser
salvas pelo viewer sem substituir o desenho que será revisado posteriormente
pelo agente.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .draw import _atomic_write, _is_draw_id, read_draw

IMPROVEMENT_VERSION = 1
IMPROVEMENT_STATUSES = {"draft", "ready", "applied"}
IMPROVEMENT_QUESTION_COUNT = 10
IMPROVEMENT_TYPES = {"choice", "boolean", "open"}
IMPROVEMENT_ID_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")


def improvements_directory(root: Path) -> Path:
    """Retorna o armazenamento separado das sessões do Draw Improve."""
    return root / ".stdd" / "improvements"


def improvement_index_path(root: Path) -> Path:
    """Retorna o índice leve das sessões de melhoria."""
    return improvements_directory(root) / "index.json"


def ensure_improvement_workspace(root: Path) -> list[Path]:
    """Cria o diretório e o índice das sessões de forma idempotente."""
    directory = improvements_directory(root)
    created: list[Path] = []
    if not directory.exists():
        directory.mkdir(parents=True, exist_ok=True)
        created.append(directory)
    index_path = improvement_index_path(root)
    if not index_path.exists():
        _atomic_write(index_path, json.dumps({"version": IMPROVEMENT_VERSION, "improvements": []}, indent=2) + "\n")
        created.append(index_path)
    return created


def read_improvement_index(root: Path) -> dict[str, Any]:
    """Lê o índice operacional sem carregar as sessões completas."""
    ensure_improvement_workspace(root)
    try:
        index = json.loads(improvement_index_path(root).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"índice de melhorias inválido: {error.__class__.__name__}") from error
    if not isinstance(index, dict) or not isinstance(index.get("improvements"), list):
        raise ValueError("índice de melhorias deve conter improvements como lista")
    return index


def _answered(answer: Any) -> bool:
    """Determina se uma resposta foi preenchida sem descartar false ou zero."""
    return answer is not None and not (isinstance(answer, str) and not answer.strip())


def _session_status(questions: list[dict[str, Any]]) -> str:
    """Calcula o estado editável a partir das dez respostas persistidas."""
    return "ready" if all(isinstance(question, dict) and _answered(question.get("answer")) for question in questions) else "draft"


def _is_improvement_id(value: Any) -> bool:
    return isinstance(value, str) and bool(IMPROVEMENT_ID_PATTERN.fullmatch(value))


def _validate_choice_question(prefix: str, question: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    options = question.get("options")
    if not isinstance(options, list) or not 2 <= len(options) <= 4:
        violations.append(f"{prefix}.options deve conter de 2 a 4 opções")
        options = options if isinstance(options, list) else []
    option_ids: set[int] = set()
    for option_index, option in enumerate(options):
        option_prefix = f"{prefix}.options[{option_index}]"
        if not isinstance(option, dict) or not isinstance(option.get("id"), int) or isinstance(option.get("id"), bool):
            violations.append(f"{option_prefix}.id deve ser numérico")
            continue
        option_id = option["id"]
        if option_id in option_ids:
            violations.append(f"opção duplicada em {prefix}: {option_id}")
        option_ids.add(option_id)
        if not isinstance(option.get("label"), str) or not option["label"].strip():
            violations.append(f"{option_prefix}.label é obrigatório")
    answer = question.get("answer")
    is_selected_option = isinstance(answer, int) and not isinstance(answer, bool) and answer in option_ids
    is_custom_answer = isinstance(answer, str) and bool(answer.strip())
    if answer is not None and not (is_selected_option or is_custom_answer):
        violations.append(f"{prefix}.answer deve apontar para uma opção existente ou conter uma resposta livre")
    return violations


def _validate_typed_question(prefix: str, question: dict[str, Any]) -> list[str]:
    question_type = question.get("type")
    answer = question.get("answer")
    if question_type == "choice":
        return _validate_choice_question(prefix, question)
    if "options" in question:
        violations = [f"{prefix} {question_type} não deve declarar options"]
    else:
        violations = []
    if question_type == "boolean" and answer is not None and not (
        isinstance(answer, bool) or (isinstance(answer, str) and bool(answer.strip()))
    ):
        violations.append(f"{prefix}.answer deve ser booleano ou nulo")
    if question_type == "open" and answer is not None and not isinstance(answer, str):
        violations.append(f"{prefix}.answer deve ser texto ou nulo")
    return violations


def _validate_question(prefix: str, question: Any, question_ids: set[int]) -> list[str]:
    if not isinstance(question, dict) or not isinstance(question.get("id"), int) or isinstance(question.get("id"), bool):
        return [f"{prefix}.id deve ser numérico"]
    violations: list[str] = []
    question_id = question["id"]
    if question_id in question_ids:
        violations.append(f"pergunta duplicada: {question_id}")
    question_ids.add(question_id)
    if not isinstance(question.get("prompt"), str) or not question["prompt"].strip():
        violations.append(f"{prefix}.prompt é obrigatório")
    if question.get("type") not in IMPROVEMENT_TYPES:
        violations.append(f"{prefix}.type deve ser choice, boolean ou open")
        return violations
    return violations + _validate_typed_question(prefix, question)


def validate_improvement_payload(payload: Any, *, allow_applied: bool = True) -> list[str]:
    """Valida o contrato lógico de uma sessão de melhoria."""
    if not isinstance(payload, dict):
        return ["a sessão de melhoria deve ser um objeto JSON"]

    violations: list[str] = []
    if payload.get("version", IMPROVEMENT_VERSION) != IMPROVEMENT_VERSION:
        violations.append("version da sessão deve ser 1")
    if not _is_improvement_id(payload.get("id")):
        violations.append("id da sessão deve ser descritivo, minúsculo e seguro")
    if not isinstance(payload.get("title"), str) or not payload["title"].strip():
        violations.append("title é obrigatório")
    if not _is_draw_id(payload.get("draw_id")):
        violations.append("draw_id deve ser um ID de desenho seguro")

    status = payload.get("status", "draft")
    if status not in IMPROVEMENT_STATUSES or (status == "applied" and not allow_applied):
        violations.append("status deve ser draft, ready ou applied")

    questions = payload.get("questions")
    if not isinstance(questions, list) or len(questions) != IMPROVEMENT_QUESTION_COUNT:
        violations.append(f"questions deve conter exatamente {IMPROVEMENT_QUESTION_COUNT} perguntas")
        questions = questions if isinstance(questions, list) else []

    question_ids: set[int] = set()
    for index, question in enumerate(questions):
        violations.extend(_validate_question(f"questions[{index}]", question, question_ids))

    if questions and status == "ready" and _session_status(questions) != "ready":
        violations.append("status ready exige as dez perguntas respondidas")
    if questions and status == "draft" and _session_status(questions) == "ready":
        violations.append("status draft não pode conter as dez perguntas respondidas")
    if questions and status == "applied" and _session_status(questions) != "ready":
        violations.append("status applied exige as dez perguntas respondidas")
    return violations


def _metadata(payload: dict[str, Any], timestamp: str) -> dict[str, Any]:
    questions = payload["questions"]
    return {
        "id": payload["id"],
        "file": f"{payload['id']}.json",
        "title": payload["title"],
        "draw_id": payload["draw_id"],
        "status": payload["status"],
        "answered_count": sum(1 for question in questions if _answered(question.get("answer"))),
        "question_count": len(questions),
        "updated_at": timestamp,
    }


def _write_index(root: Path, entries: list[dict[str, Any]]) -> None:
    entries.sort(key=lambda entry: (str(entry.get("updated_at", "")), str(entry.get("id", ""))))
    _atomic_write(
        improvement_index_path(root),
        json.dumps({"version": IMPROVEMENT_VERSION, "improvements": entries}, indent=2, ensure_ascii=False) + "\n",
    )


def create_improvement(root: Path, payload: dict[str, Any]) -> Path:
    """Cria ou atualiza uma sessão editável sem escrever no Draw associado."""
    if not isinstance(payload, dict):
        raise ValueError("Sessão de melhoria inválida: a sessão deve ser um objeto JSON")
    document = deepcopy(payload)
    document.setdefault("version", IMPROVEMENT_VERSION)
    document.setdefault("status", "draft")
    if isinstance(document.get("questions"), list) and len(document["questions"]) == IMPROVEMENT_QUESTION_COUNT:
        if document.get("status") != "applied":
            document["status"] = _session_status(document["questions"])
    violations = validate_improvement_payload(document, allow_applied=False)
    if violations:
        raise ValueError("Sessão de melhoria inválida: " + "; ".join(violations))
    read_draw(root, document["draw_id"])
    ensure_improvement_workspace(root)
    output = improvements_directory(root) / f"{document['id']}.json"
    index = read_improvement_index(root)
    existing_entry = next((entry for entry in index["improvements"] if entry.get("id") == document["id"]), None)
    if existing_entry:
        try:
            existing = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("sessão de melhoria existente está inválida") from error
        if existing.get("status") == "applied":
            raise ValueError("sessão de melhoria aplicada é imutável")
        document.setdefault("created_at", existing.get("created_at"))
    timestamp = datetime.now(timezone.utc).isoformat()
    document["status"] = _session_status(document["questions"])
    document["updated_at"] = timestamp
    _atomic_write(output, json.dumps(document, indent=2, ensure_ascii=False) + "\n")
    entries = [entry for entry in index["improvements"] if entry.get("id") != document["id"]]
    entries.append(_metadata(document, timestamp))
    _write_index(root, entries)
    return output


def read_improvement(root: Path, improvement_id: str) -> dict[str, Any]:
    """Lê e valida uma sessão individual."""
    if not _is_improvement_id(improvement_id):
        raise ValueError("id de melhoria inválido")
    path = improvements_directory(root) / f"{improvement_id}.json"
    if not path.exists():
        raise ValueError(f"sessão de melhoria não encontrada: {improvement_id}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"sessão de melhoria inválida: {error.__class__.__name__}") from error
    violations = validate_improvement_payload(payload)
    if violations:
        raise ValueError("Sessão de melhoria inválida: " + "; ".join(violations))
    return payload


def list_ready_improvements(root: Path) -> list[dict[str, Any]]:
    """Retorna sessões completas que aguardam aplicação pelo agente."""
    ready: list[dict[str, Any]] = []
    for entry in read_improvement_index(root).get("improvements", []):
        if not isinstance(entry, dict) or entry.get("status") != "ready":
            continue
        improvement_id = entry.get("id")
        if not isinstance(improvement_id, str):
            continue
        document = read_improvement(root, improvement_id)
        if document.get("status") != "ready":
            continue
        document["improvement_file"] = f".stdd/improvements/{improvement_id}.json"
        document["draw_file"] = f".stdd/draws/{document['draw_id']}.json"
        ready.append(document)
    return ready


def mark_improvement_applied(root: Path, improvement_id: str) -> Path:
    """Marca uma sessão pronta como aplicada, preservando seu histórico."""
    document = read_improvement(root, improvement_id)
    if document.get("status") != "ready":
        raise ValueError("somente uma sessão ready pode ser marcada como applied")
    read_draw(root, document["draw_id"])
    timestamp = datetime.now(timezone.utc).isoformat()
    document["status"] = "applied"
    document["updated_at"] = timestamp
    output = improvements_directory(root) / f"{improvement_id}.json"
    _atomic_write(output, json.dumps(document, indent=2, ensure_ascii=False) + "\n")
    index = read_improvement_index(root)
    entries = [entry for entry in index["improvements"] if entry.get("id") != improvement_id]
    entries.append(_metadata(document, timestamp))
    _write_index(root, entries)
    return output
