"""Leitura e persistência da configuração consolidada do Looper.

Projetos novos usam um único arquivo YAML. Os três arquivos da configuração
anterior são lidos uma vez e migrados automaticamente para preservar upgrades.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
import re
from typing import Any

import yaml

CONFIG_RELATIVE_PATH = ".looper/config.yaml"
LEGACY_CONFIG_RELATIVE_PATH = ".looper/config.json"
LEGACY_REVIEW_RELATIVE_PATH = ".looper/review-agents.json"
LEGACY_INSTRUCTIONS_RELATIVE_PATH = ".looper/loop-instructions.md"

CONFIG_COMMENTS = {
    "test_commands": "Suítes executadas por `looper test`; cada item aceita name, command e timeout.",
    "test_commands.name": "Nome legível exibido no relatório da suíte.",
    "test_commands.command": "Comando executado como lista de argumentos, sem shell intermediário.",
    "testing": "Preferências gerais da execução de testes.",
    "testing.profile": "Perfil de testes usado pelo runner, normalmente `mvp`.",
    "contract": "Regras de documentação e contrato dos testes.",
    "contract.enabled": "Ativa ou desativa a validação de contrato.",
    "contract.code_language": "Linguagem cujo contrato será analisado.",
    "contract.description_language": "Idioma esperado nas descrições dos testes.",
    "contract.short_description_max_chars": "Limite de caracteres para descrições curtas.",
    "static_analysis": "Configuração do adaptador e dos gates de análise estática.",
    "static_analysis.enabled": "Ativa ou desativa a análise estática.",
    "static_analysis.adapter_command": "Comando do adaptador; use uma lista de argumentos.",
    "static_analysis.contract_version": "Versão do contrato retornado pelo adaptador.",
    "static_analysis.allow_marked_test_credentials": "Permite que credenciais marcadas em fixtures sejam apenas warnings.",
    "static_analysis.quality": "Limites de qualidade que geram warnings ou bloqueios.",
    "static_analysis.exceptions": "Exceções temporárias e rastreáveis para achados específicos.",
    "tracked_extensions": "Extensões consideradas no cálculo de alterações do projeto.",
    "backlog": "Ordem, lotes e comportamento dos loops do backlog.",
    "backlog.development_mode": "`sequential` mistura fases; `separated` conclui L2 antes de L3.",
    "backlog.bootstrap_task": "Habilita a task inicial de preparação do projeto.",
    "backlog.final_verification_task": "Cria uma verificação final após as tasks do backlog.",
    "backlog.task_batch_size": "Quantidade máxima de itens entregues em cada avanço.",
    "backlog.task_batch_scope": "Escopo do lote: `task` ou `node`.",
    "backlog.task_delivery_scope": "Escopo comum da entrega: task individual ou nó completo.",
    "backlog.test_loop_enabled": "Habilita o loop que cria e libera testes.",
    "backlog.test_loop": "Preset e opções do loop de testes.",
    "backlog.implementation_loop": "Preset e opções do loop de implementação.",
    "instructions": "Orientações persistentes enviadas ao agente em todas as entregas.",
    "review": "Revisão automática opcional após tasks concluídas.",
    "review.enabled": "Ativa a execução automática de revisões.",
    "review.default_agent": "Agente padrão: `codex`, `claude` ou `antigravity`.",
    "review.agents.*.model": "Modelo usado pelo agente específico; a substituição manual pela CLI continua disponível.",
    "review.reasoning": "Nível de reasoning usado quando o agente aceitar essa opção.",
    "review.timeout_seconds": "Tempo máximo da revisão em segundos.",
    "review.standard_prompt": "Prompt base enviado ao agente de revisão.",
    "review.triggers": "Define em quais fases e escopos a revisão é acionada.",
    "review.agents": "Comandos locais disponíveis para cada agente.",
    "version": "Versão do esquema da configuração.",
    "stack": "Stack detectada localmente; normalmente atualizada por `looper setup`.",
}


def _annotate_yaml(content: str) -> str:
    """Insere documentação antes de cada chave YAML sem alterar os valores."""
    stack: list[tuple[int, str]] = []
    output: list[str] = []
    key_pattern = re.compile(r"^(\s*)([^#\s][^:]*):(?:\s|$)")
    for line in content.splitlines():
        match = key_pattern.match(line)
        if match:
            indent = len(match.group(1).replace("\t", "    "))
            key = match.group(2).strip().strip("'\"")
            while stack and stack[-1][0] >= indent:
                stack.pop()
            path = ".".join([item[1] for item in stack] + [key])
            comment = CONFIG_COMMENTS.get(path, f"Opção `{path}` da configuração.")
            output.append(f"{match.group(1)}# {comment}")
            stack.append((indent, key))
        output.append(line)
    return "\n".join(output) + "\n"


def config_path(root: Path) -> Path:
    return root / CONFIG_RELATIVE_PATH


def _read_mapping(path: Path, parser: Any) -> dict[str, Any]:
    try:
        value = parser(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, yaml.YAMLError) as error:
        raise ValueError(f"configuração inválida em {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"configuração em {path} deve ser um objeto")
    return value


def _legacy_documents(root: Path) -> dict[str, Any] | None:
    old_config = root / LEGACY_CONFIG_RELATIVE_PATH
    old_review = root / LEGACY_REVIEW_RELATIVE_PATH
    old_instructions = root / LEGACY_INSTRUCTIONS_RELATIVE_PATH
    if not any(path.exists() for path in (old_config, old_review, old_instructions)):
        return None
    config = _read_mapping(old_config, json.loads) if old_config.exists() else {}
    review = _read_mapping(old_review, json.loads) if old_review.exists() else {}
    instructions = old_instructions.read_text(encoding="utf-8") if old_instructions.exists() else ""
    config["review"] = review
    config["instructions"] = instructions
    return config


def load_config(root: Path, *, migrate: bool = True) -> dict[str, Any]:
    path = config_path(root)
    if path.exists():
        return _read_mapping(path, yaml.safe_load)
    legacy = _legacy_documents(root)
    if legacy is not None:
        if migrate:
            save_config(root, legacy)
        return legacy
    return {}


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save_config(root: Path, data: dict[str, Any]) -> Path:
    if not isinstance(data, dict):
        raise ValueError("configuração deve ser um objeto")
    path = config_path(root)
    serialized = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False)
    _atomic_write(path, _annotate_yaml(serialized))
    # Remoção somente depois do YAML estar persistido com sucesso.
    for relative in (LEGACY_CONFIG_RELATIVE_PATH, LEGACY_REVIEW_RELATIVE_PATH, LEGACY_INSTRUCTIONS_RELATIVE_PATH):
        legacy = root / relative
        if legacy.exists():
            legacy.unlink()
    return path


def default_config() -> dict[str, Any]:
    return {"test_commands": [], "testing": {"profile": "mvp"}, "contract": {"enabled": True}, "static_analysis": {"enabled": True}, "tracked_extensions": [], "backlog": {"development_mode": "sequential"}, "version": 1}


def review_config(data: dict[str, Any]) -> dict[str, Any]:
    value = data.get("review", {})
    return value if isinstance(value, dict) else {}


def instructions(data: dict[str, Any]) -> str:
    value = data.get("instructions", "")
    return value if isinstance(value, str) else ""
