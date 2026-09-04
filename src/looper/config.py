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
    "test_commands": "Comandos de teste executados por `looper test`. Cada item precisa de name e command.",
    "test_commands.name": "Nome legível exibido no relatório de testes.",
    "test_commands.command": "Comando executado como lista de argumentos, sem shell intermediário.",
    "test_commands.type": "Tipo da suíte: use `playwright` para testes de tela no navegador; requer `looper test --playwright`.",
    "testing": "Preferências gerais de como os testes são executados.",
    "testing.profile": "Perfil de testes do runner, normalmente `mvp`.",
    "contract": "Validação automática da documentação dos testes.",
    "contract.enabled": "Ativa a validação automática da documentação dos testes.",
    "contract.code_language": "Linguagem cujo contrato será analisado.",
    "contract.description_language": "Idioma esperado nas descrições dos testes.",
    "contract.short_description_max_chars": "Limite de caracteres para descrições curtas.",
    "static_analysis": "Análise de qualidade: complexidade, dependências e estrutura do código.",
    "static_analysis.enabled": "Ativa a análise de qualidade do código; requer adaptador configurado.",
    "static_analysis.adapter_command": "Comando do adaptador; use uma lista de argumentos.",
    "static_analysis.contract_version": "Versão do contrato retornado pelo adaptador.",
    "static_analysis.allow_marked_test_credentials": "Permite que credenciais marcadas em fixtures sejam apenas warnings.",
    "static_analysis.quality": "Limites de qualidade que geram warnings ou bloqueios.",
    "static_analysis.exceptions": "Exceções temporárias e rastreáveis para achados específicos.",
    "tracked_extensions": "Extensões consideradas no cálculo de alterações do projeto.",
    "backlog": "Ordem, lotes e comportamento dos loops de desenvolvimento.",
    "backlog.development_mode": "Ordem de desenvolvimento: `sequential` intercala telas e backend; `separated` conclui todas as telas antes do backend.",
    "backlog.bootstrap_task": "Habilita a task inicial de preparação do projeto.",
    "backlog.final_verification_task": "Cria uma verificação final após as tasks do backlog.",
    "backlog.task_batch_size": "Quantidade máxima de itens entregues em cada avanço.",
    "backlog.l4_group_size": "Quantidade de nós L4 entregues junto com o pai L3; padrão 3.",
    "backlog.task_batch_scope": "Escopo do lote: `task` ou `node`.",
    "backlog.task_delivery_scope": "Tamanho de cada entrega: `task` (uma por vez) ou `node` (nó completo com subfluxos).",
    "backlog.test_loop_enabled": "Cria e libera testes antes de implementar.",
    "backlog.test_loop": "Sequência e opções do loop de testes.",
    "backlog.test_scope": "O que será testado: `l2` (telas), `l3` (backend) ou `both` (ambos).",
    "backlog.implementation_loop": "Preset e opções do loop de implementação.",
    "instructions": "Orientações persistentes enviadas ao agente por tipo de loop.",
    "instructions.backend": "Enviado em todo loop de backend (backlog backend / backlog task --backend).",
    "instructions.frontend": "Enviado em todo loop de frontend (backlog frontend / backlog task --frontend).",
    "instructions.change": "Enviado em todo loop de alteração (backlog change).",
    "review": "Revisão automática opcional após tasks concluídas.",
    "review.enabled": "Ativa a execução automática de revisões.",
    "review.interval_tasks": "Executa a revisão depois de cada N tasks concluídas; 1 revisa cada task.",
    "review.execution_mode": "Modo de chamada do subagente: somente `tmux`.",
    "review.default_agent": "Agente de revisão padrão: `agy`; `codex` também pode ser escolhido nas configurações.",
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
            comment = CONFIG_COMMENTS.get(path, f"Configuração de {path.split('.')[-1].replace('_', ' ')}.")
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


DEFAULT_BACKEND_LOGGING_INSTRUCTION = (
    "Logging transversal obrigatório: registre eventos em todas as etapas, funções públicas, handlers e integrações usando a fachada central de log do projeto. "
    "Mantenha rastreabilidade completa (entrada e saída com parâmetros em debug, conclusão de operações em info, erros incondicionais com stack trace cru em error). "
    "Não use print ou console.log ad-hoc. "
    "Evite arquivos de back-end com mais de 300 linhas; esta é uma orientação de projeto para manter o backend modular, não um limite ou validação estática do looper test."
)


def _migrate_instructions(instructions_val: Any) -> dict[str, str]:
    """Migra instructions legado para o formato dict injetando a diretiva de logging no backend."""
    backend_instr = DEFAULT_BACKEND_LOGGING_INSTRUCTION
    if isinstance(instructions_val, str):
        raw = instructions_val.strip()
        if raw:
            if DEFAULT_BACKEND_LOGGING_INSTRUCTION not in raw:
                backend_instr = f"{raw}\n\n{DEFAULT_BACKEND_LOGGING_INSTRUCTION}"
            else:
                backend_instr = raw
        return {
            "backend": backend_instr,
            "frontend": "",
            "change": "",
        }
    if isinstance(instructions_val, dict):
        result = {str(k): str(v) for k, v in instructions_val.items()}
        current_backend = result.get("backend", "").strip()
        if not current_backend:
            result["backend"] = DEFAULT_BACKEND_LOGGING_INSTRUCTION
        elif DEFAULT_BACKEND_LOGGING_INSTRUCTION not in current_backend:
            result["backend"] = f"{current_backend}\n\n{DEFAULT_BACKEND_LOGGING_INSTRUCTION}"
        result.setdefault("frontend", "")
        result.setdefault("change", "")
        return result
    return {
        "backend": DEFAULT_BACKEND_LOGGING_INSTRUCTION,
        "frontend": "",
        "change": "",
    }


def _legacy_documents(root: Path) -> dict[str, Any] | None:
    old_config = root / LEGACY_CONFIG_RELATIVE_PATH
    old_review = root / LEGACY_REVIEW_RELATIVE_PATH
    old_instructions = root / LEGACY_INSTRUCTIONS_RELATIVE_PATH
    if not any(path.exists() for path in (old_config, old_review, old_instructions)):
        return None
    config = _read_mapping(old_config, json.loads) if old_config.exists() else {}
    review = _read_mapping(old_review, json.loads) if old_review.exists() else {}
    raw_instructions = old_instructions.read_text(encoding="utf-8") if old_instructions.exists() else ""
    config["review"] = review
    config["instructions"] = _migrate_instructions(raw_instructions)
    return config


def load_config(root: Path, *, migrate: bool = True) -> dict[str, Any]:
    path = config_path(root)
    if path.exists():
        data = _read_mapping(path, yaml.safe_load)
        if isinstance(data.get("instructions"), str) or not isinstance(data.get("instructions"), dict):
            data["instructions"] = _migrate_instructions(data.get("instructions"))
            if migrate:
                save_config(root, data)
        return data
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
    return {"test_commands": [], "testing": {"profile": "mvp"}, "contract": {"enabled": True}, "static_analysis": {"enabled": True}, "tracked_extensions": [], "backlog": {"development_mode": "sequential", "l4_group_size": 3}, "instructions": {"backend": DEFAULT_BACKEND_LOGGING_INSTRUCTION, "frontend": "", "change": ""}, "version": 1}


def review_config(data: dict[str, Any]) -> dict[str, Any]:
    value = data.get("review", {})
    return value if isinstance(value, dict) else {}


def instructions(data: dict[str, Any]) -> str:
    """Retorna a string de instruções persistentes para retrocompatibilidade.

    Se o campo for dict (novo schema), une todas as entradas não-vazias separadas por
    newline. Se for str (schema legado), retorna a string diretamente.
    """
    value = data.get("instructions", "")
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        parts = [v.strip() for v in value.values() if isinstance(v, str) and v.strip()]
        return "\n".join(parts)
    return ""


def instructions_for(data: dict[str, Any], phase: str | None) -> str:
    """Retorna a instrução persistente para a fase específica do loop.

    - ``phase`` aceita 'backend', 'frontend' ou 'change'.
    - Fases sem mapeamento explícito ('test', 'bootstrap', ``None``) usam a instrução
      'backend' como fallback, pois essas fases sempre precedem ou compõem o backend.
    - Se ``instructions`` for str (projeto legado), retorna a string para qualquer fase.
    """
    value = data.get("instructions", "")
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return ""
    phase_key = phase if phase in ("backend", "frontend", "change") else "backend"
    result = value.get(phase_key, "")
    return result.strip() if isinstance(result, str) else ""
