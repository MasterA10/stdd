"""Revisão opcional de tasks concluídas por agentes CLI externos.

O resultado da revisão é determinado pelas changes criadas no Draw, nunca por
um formato específico de stdout do agente. Isso mantém o contrato natural do
Looper e permite trocar o comando de qualquer agente pela configuração local.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .draw import add_draw_change, draw_directory, read_draw
from .config import load_config, save_config

REVIEW_CONFIG_FILE = ".looper/config.yaml"
REVIEW_HISTORY_DIRECTORY = ".looper/reviews"
VALID_REVIEW_AGENTS = {"codex", "agy", "claude", "antigravity"}
VALID_REVIEW_SCOPES = {"l2", "l3", "l2_and_l3", "all"}
VALID_REVIEW_EVENTS = {"test", "implementation", "change"}

DEFAULT_REVIEW_CONFIG: dict[str, Any] = {
    "enabled": False,
    "default_agent": "agy",
    "interval_tasks": 1,
    "execution_mode": "terminal",
    "completed_since_last_review": 0,
    "reasoning": "high",
    "timeout_seconds": 900,
    "standard_prompt": (
        "Confira a task aprovada abaixo usando o Draw e os arquivos reais do projeto. "
        "Não implemente código. Se faltar algo, crie uma change pendente no nó exato "
        "usando `looper draw change add`; se estiver completa, não crie nenhuma change."
    ),
    "triggers": {
        "test": {"l2": False, "l3": False, "l2_and_l3": False, "all": False},
        "implementation": {"l2": True, "l3": True, "l2_and_l3": False, "all": False},
        "change": {"l2": False, "l3": False, "l2_and_l3": False, "all": False},
    },
    "agents": {
        "codex": {"model": "", "command": ["codex", "exec", "--model", "{model}", "-c", "model_reasoning_effort={reasoning}", "{prompt}"]},
        "claude": {"model": "", "command": ["claude", "-p", "--model", "{model}", "{prompt}"]},
        "agy": {"model": "", "command": ["agy", "-p", "{prompt}", "--dangerously-skip-permissions", "--effort", "{reasoning}", "--model", "{model}"]},
        "antigravity": {"model": "", "command": ["agy", "-p", "{prompt}", "--dangerously-skip-permissions", "--effort", "{reasoning}", "--model", "{model}"]},
    },
}


def review_config_path(root: Path) -> Path:
    return root / REVIEW_CONFIG_FILE


def review_history_directory(root: Path) -> Path:
    return root / REVIEW_HISTORY_DIRECTORY


def ensure_review_workspace(root: Path) -> list[Path]:
    """Cria configuração e histórico sem substituir escolhas do projeto."""
    changed: list[Path] = []
    directory = review_history_directory(root)
    if not directory.exists():
        directory.mkdir(parents=True)
        changed.append(directory)
    data = load_config(root)
    if not isinstance(data.get("review"), dict) or not data["review"]:
        data["review"] = json.loads(json.dumps(DEFAULT_REVIEW_CONFIG))
        save_config(root, data)
        changed.append(review_config_path(root))
    return changed


def load_review_config(root: Path) -> dict[str, Any]:
    ensure_review_workspace(root)
    try:
        data = load_config(root).get("review", {})
    except (OSError, ValueError) as error:
        raise ValueError(f"configuração de revisão inválida: {error}") from error
    if not isinstance(data, dict):
        raise ValueError("configuração de revisão deve ser um objeto")
    changed = False
    legacy_interval = load_config(root).get("backlog", {}).get("verification_interval", 0)
    if "interval_tasks" not in data and legacy_interval:
        try:
            data["interval_tasks"] = max(1, int(legacy_interval))
        except (TypeError, ValueError):
            data["interval_tasks"] = 1
        changed = True
    for key, value in (("interval_tasks", 1), ("execution_mode", "terminal"), ("completed_since_last_review", 0)):
        if key not in data:
            data[key] = value
            changed = True
    if data.get("execution_mode") not in {"terminal", "tmux"}:
        data["execution_mode"] = "terminal"
        changed = True
    if changed:
        project = load_config(root)
        project["review"] = data
        save_config(root, project)
    return data


def set_review_enabled(root: Path, enabled: bool) -> dict[str, Any]:
    """Ativa ou desativa o acionamento automático das revisões."""
    data = load_config(root)
    config = load_review_config(root)
    config["enabled"] = bool(enabled)
    data["review"] = config
    save_config(root, data)
    return config


def _draw_change_snapshot(root: Path) -> dict[tuple[str, int, int], dict[str, Any]]:
    snapshot: dict[tuple[str, int, int], dict[str, Any]] = {}
    directory = draw_directory(root)
    for path in sorted(directory.glob("*.json")):
        if path.name == "index.json":
            continue
        document = read_draw(root, path.stem)
        for node in document.get("nodes", []):
            for change in node.get("changes", []):
                if isinstance(change, dict) and isinstance(change.get("id"), int):
                    snapshot[(path.stem, node.get("id"), change["id"])] = change
    return snapshot


def _task_scope(task: dict[str, Any], requested: str | None) -> str:
    if requested:
        if requested not in VALID_REVIEW_SCOPES:
            raise ValueError("escopo inválido; use l2, l3, l2_and_l3 ou all")
        return requested
    return "l2" if task.get("level") == 2 else "l3"


def _configured_scope(config: dict[str, Any], event: str, task: dict[str, Any]) -> str | None:
    """Escolhe o preset mais abrangente habilitado para a camada entregue."""
    triggers = config.get("triggers", {}).get(event, {})
    base = _task_scope(task, None)
    candidates = ["l2_and_l3", "all", "l2"] if base == "l2" else ["all", "l3"]
    return next((scope for scope in candidates if triggers.get(scope, False)), None)


def _target_context(root: Path, task: dict[str, Any], scope: str) -> list[dict[str, Any]]:
    draw_id = task.get("draw_id")
    node_id = task.get("node_id")
    if not isinstance(draw_id, str) or not isinstance(node_id, int):
        return [{"draw_id": draw_id, "node_id": node_id, "label": task.get("label", task.get("id"))}]
    targets: list[dict[str, Any]] = []
    document = read_draw(root, draw_id)
    node = next((item for item in document.get("nodes", []) if item.get("id") == node_id), None)
    if node is not None and scope in {"l2", "l2_and_l3", "all"}:
        targets.append({"draw_id": draw_id, "node_id": node_id, "label": node.get("label")})
        if scope in {"l2_and_l3", "all"}:
            for child_id in node.get("draw_ref"),:
                if isinstance(child_id, str):
                    child = read_draw(root, child_id)
                    parent_node = child.get("hierarchy", {}).get("parent_node_id")
                    for child_node in child.get("nodes", []):
                        if parent_node == node_id or scope == "all":
                            targets.append({"draw_id": child_id, "node_id": child_node.get("id"), "label": child_node.get("label")})
    if scope in {"l3", "all"} and not any(item["draw_id"] == draw_id and item["node_id"] == node_id for item in targets):
        targets.append({"draw_id": draw_id, "node_id": node_id, "label": task.get("label")})
    return targets


def _prompt(config: dict[str, Any], task: dict[str, Any], scope: str, targets: list[dict[str, Any]]) -> str:
    standard = str(config.get("standard_prompt", "")).strip()
    target_lines = "\n".join(f"- {item['draw_id']} / nó {item['node_id']}: {item.get('label', '')}" for item in targets)
    return (
        f"{standard}\n\nTask aprovada: {task.get('id')} — {task.get('label', '')}\n"
        f"Escopo da revisão: {scope}\nNós que podem receber changes:\n{target_lines}\n\n"
        "Uma ausência de change significa aprovação. Se encontrar mais de uma lacuna, crie uma change para cada lacuna."
    )


def _command(config: dict[str, Any], agent: str, model: str, reasoning: str, prompt: str) -> list[str]:
    agents = config.get("agents", {})
    entry = agents.get(agent, {}) if isinstance(agents, dict) else {}
    command = entry.get("command") if isinstance(entry, dict) else None
    if not isinstance(command, list) or not command:
        raise ValueError(f"agente {agent} não possui comando configurado")
    values = {"model": model, "reasoning": reasoning, "prompt": prompt}
    rendered = [str(part).format(**values) for part in command]
    if not model:
        rendered = [part for index, part in enumerate(rendered) if not (part == "--model" or (index and rendered[index - 1] == "--model"))]
    if not reasoning:
        rendered = [part for part in rendered if not part.startswith("model_reasoning_effort=")]
        rendered = [part for index, part in enumerate(rendered) if not (part == "-c" and index + 1 < len(rendered) and rendered[index + 1].startswith("model_reasoning_effort="))]
        rendered = [part for index, part in enumerate(rendered) if not (part == "--effort" or (index and rendered[index - 1] == "--effort"))]
    return rendered


def _run_terminal(command: list[str], root: Path, timeout: int) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=timeout, check=False)
        return completed.returncode, completed.stdout, completed.stderr
    except (OSError, subprocess.TimeoutExpired) as error:
        return -1, "", str(error)


def _run_tmux(command: list[str], root: Path, timeout: int, review_id: str) -> tuple[int, str, str]:
    """Executa o CLI do agente em uma sessão tmux e aguarda seu término."""
    session = f"looper-review-{review_id[:10]}"
    output_path = root / ".looper" / "reviews" / f".{review_id}.output"
    marker = "__LOOPER_REVIEW_EXIT__"
    script = f"{shlex.join(command)} > {shlex.quote(str(output_path))} 2>&1; printf '\\n{marker}%s\\n' $? >> {shlex.quote(str(output_path))}"
    try:
        launched = subprocess.run(["tmux", "new-session", "-d", "-s", session, "sh", "-lc", script], cwd=root, capture_output=True, text=True, timeout=15, check=False)
        if launched.returncode != 0:
            return launched.returncode, launched.stdout, launched.stderr
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not subprocess.run(["tmux", "has-session", "-t", session], cwd=root, capture_output=True, text=True, check=False).returncode == 0:
                break
            time.sleep(0.25)
        else:
            subprocess.run(["tmux", "kill-session", "-t", session], cwd=root, capture_output=True, text=True, check=False)
            return -1, "", f"revisão excedeu o tempo limite de {timeout}s"
        content = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
        returncode = -1
        if marker in content:
            output, exit_value = content.rsplit(marker, 1)
            try:
                returncode = int(exit_value.strip().splitlines()[0])
            except (IndexError, ValueError):
                output = content
            content = output
        return returncode, content, ""
    except (OSError, subprocess.TimeoutExpired) as error:
        return -1, "", str(error)
    finally:
        if output_path.exists():
            output_path.unlink()


def _run_agent(config: dict[str, Any], command: list[str], root: Path, timeout: int, review_id: str) -> tuple[int, str, str]:
    if config.get("execution_mode", "terminal") == "tmux":
        return _run_tmux(command, root, timeout, review_id)
    return _run_terminal(command, root, timeout)


def run_review(
    root: Path,
    task: dict[str, Any],
    *,
    event: str = "implementation",
    agent: str | None = None,
    scope: str | None = None,
    model: str | None = None,
    reasoning: str | None = None,
    force: bool = True,
) -> dict[str, Any]:
    """Executa uma revisão e registra evidência; falha não reabre a task."""
    if event not in VALID_REVIEW_EVENTS:
        raise ValueError("fase de revisão inválida")
    config = load_review_config(root)
    selected_agent = agent or config.get("default_agent", "agy")
    if selected_agent not in VALID_REVIEW_AGENTS:
        raise ValueError("agente inválido; use codex ou agy")
    selected_scope = _task_scope(task, scope)
    trigger = config.get("triggers", {}).get(event, {}).get(selected_scope, False)
    if not force and not (config.get("enabled", False) and trigger):
        return {"status": "skipped", "reason": "gatilho desabilitado", "scope": selected_scope}
    agent_config = config.get("agents", {}).get(selected_agent, {})
    configured_model = agent_config.get("model", config.get("model", "")) if isinstance(agent_config, dict) else config.get("model", "")
    selected_model = model if model is not None else str(configured_model)
    selected_reasoning = reasoning if reasoning is not None else str(config.get("reasoning", ""))
    targets = _target_context(root, task, selected_scope)
    prompt = _prompt(config, task, selected_scope, targets)
    command = _command(config, selected_agent, selected_model, selected_reasoning, prompt)
    review_id = uuid.uuid4().hex
    before = _draw_change_snapshot(root)
    started = datetime.now(timezone.utc).isoformat()
    returncode, stdout, stderr = _run_agent(config, command, root, int(config.get("timeout_seconds", 900)), review_id)
    after = _draw_change_snapshot(root)
    created = [value for key, value in after.items() if key not in before]
    status = "changes_created" if created else "approved" if returncode == 0 else "pending"
    record = {
        "id": review_id, "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
        "task_id": task.get("id"), "event": event, "scope": selected_scope, "agent": selected_agent,
        "model": selected_model, "reasoning": selected_reasoning, "command": command,
        "status": status, "returncode": returncode, "changes": created, "stdout": stdout, "stderr": stderr,
    }
    history = review_history_directory(root)
    history.mkdir(parents=True, exist_ok=True)
    (history / f"{review_id}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return record


def maybe_review_completed_task(root: Path, response: dict[str, Any]) -> dict[str, Any] | None:
    task = response.get("task")
    if not isinstance(task, dict) or response.get("status") not in {"done", "test-done"}:
        return None
    event = response.get("phase", "implementation")
    config = load_review_config(root)
    scope = _configured_scope(config, event, task)
    if not config.get("enabled", False) or scope is None:
        return None
    try:
        interval = max(1, int(config.get("interval_tasks", 1)))
        completed = max(0, int(config.get("completed_since_last_review", 0))) + 1
    except (TypeError, ValueError):
        interval, completed = 1, 1
    if completed < interval:
        config["completed_since_last_review"] = completed
        data = load_config(root)
        data["review"] = config
        save_config(root, data)
        return None
    config["completed_since_last_review"] = 0
    data = load_config(root)
    data["review"] = config
    save_config(root, data)
    return run_review(root, task, event=event, scope=scope, force=False)
