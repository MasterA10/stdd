"""Backlog derivado dos Draws e executor determinístico de jornadas."""

from __future__ import annotations

import json
from collections.abc import MutableMapping
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .draw import EDGE_CONDITIONS, create_draw, draw_directory, facts_directory, read_draw, read_draw_index
from .config import instructions, load_config, save_config


BACKLOG_VERSION = 1
VALID_TASK_STATUSES = {"pending", "in_progress", "done"}
VALID_TEST_STATUSES = {"missing", "in_progress", "done"}
VALID_EXECUTION_PHASES = {None, "bootstrap", "test", "implementation", "change"}
VALID_CHECKLIST_PHASES = {"test", "implementation"}
DEFAULT_MIN_TASK_INTERVAL_SECONDS = 0
DEFAULT_TASK_BATCH_SIZE = 1
DEFAULT_L4_GROUP_SIZE = 3
VALID_TASK_BATCH_SCOPES = {"task", "node"}
VALID_TASK_DELIVERY_SCOPES = {"task", "node"}
VALID_DEVELOPMENT_MODES = {"sequential", "separated"}
VALID_TASK_LAYERS = {"frontend", "backend"}
VALID_LOOP_MODES = {"task_order", "node_complete", "node_then_children", "all_level2_then_level3"}
VALID_CHILDREN_MODES = {"none", "context", "owned"}
LANE_CURSOR_KEYS = {
    "current_task_id", "current_backlog_id", "current_branch_id", "branch_position",
    "current_phase", "current_parent_task_id", "current_subtask_id", "lease_id",
    "lease_started_at", "lease_expires_at", "current_verified_batch_node_ids",
    "current_association_node_ids", "current_l4_group_task_ids",
}
DEFAULT_LEVEL_MEANINGS = {
    "2": "Tela",
    "3": "Regra de negócio e detalhes da tela",
    "4": "Codebase / baixo nível",
}
CRITICAL_INFORMATION_FILE = ".looper/config.yaml#instructions"


def _critical_information(root: Path) -> str:
    """Lê a orientação persistente enviada em linguagem natural a cada loop."""
    project = root.parent if root.name == ".looper" else root
    return instructions(load_config(project)).strip()


def _with_critical_instruction(instruction: str | None, content: str) -> str | None:
    """Prefixa a orientação persistente sem substituir a instrução da task."""
    if not content:
        return instruction
    block = f"INFORMAÇÃO CRÍTICA DO PROJETO:\n{content}\nFIM DA INFORMAÇÃO CRÍTICA."
    return f"{block}\n\n{instruction}" if instruction else block


class _LaneExecution(MutableMapping[str, Any]):
    """Visão compatível do execution global com cursor isolado por lane."""

    def __init__(self, execution: dict[str, Any], lane: dict[str, Any]):
        self._execution = execution
        self._lane = lane

    def __getitem__(self, key: str) -> Any:
        if key in LANE_CURSOR_KEYS:
            return self._lane.get(key)
        return self._execution[key]

    def __setitem__(self, key: str, value: Any) -> None:
        if key in LANE_CURSOR_KEYS:
            self._lane[key] = value
        else:
            self._execution[key] = value

    def __delitem__(self, key: str) -> None:
        if key in LANE_CURSOR_KEYS:
            del self._lane[key]
        else:
            del self._execution[key]

    def __iter__(self):
        return iter(set(self._execution) | set(self._lane))

    def __len__(self) -> int:
        return len(set(self._execution) | set(self._lane))


def _lane_execution(execution: dict[str, Any], phase: str, layer: str | None) -> MutableMapping[str, Any]:
    """Seleciona o cursor independente; sem camada, mantém o contrato legado."""
    if layer is None:
        return execution
    lanes = execution.setdefault("lanes", {})
    lane = lanes.setdefault(f"{phase}:{layer}", {})
    return _LaneExecution(execution, lane)


def _lane_for_task(execution: dict[str, Any], task_id: str) -> MutableMapping[str, Any]:
    """Localiza a lane que reservou uma task para permitir conclusão paralela."""
    for lane in execution.get("lanes", {}).values():
        if isinstance(lane, dict) and lane.get("current_task_id") == task_id:
            return _LaneExecution(execution, lane)
    return execution


def _normalize_loop_mode(value: object, fallback: str = "task_order") -> str:
    """Normaliza um preset de fila, preservando configurações antigas."""
    aliases = {
        "sequential": "task_order",
        "separated": "all_level2_then_level3",
        "node": "node_complete",
        "children": "node_then_children",
        "level2_then_level3": "all_level2_then_level3",
    }
    normalized = aliases.get(str(value or "").strip().casefold(), str(value or "").strip().casefold())
    return normalized if normalized in VALID_LOOP_MODES else fallback


def _loop_options(root: Path, phase: str) -> dict[str, Any]:
    """Retorna a política da fila para uma fase, com migração dos campos legados."""
    config = _get_backlog_config(root)
    legacy_mode = _development_mode(root)
    legacy_scope = config.get("task_delivery_scope", "task")
    default_mode = "all_level2_then_level3" if legacy_mode == "separated" else (
        "node_complete" if legacy_scope == "node" else "task_order"
    )
    section_name = "test_loop" if phase == "test" else "implementation_loop"
    section = config.get(section_name)
    section = section if isinstance(section, dict) else {}
    mode = _normalize_loop_mode(section.get("mode"), default_mode)
    try:
        batch_size = max(1, int(section.get("batch_size", config.get("task_batch_size", DEFAULT_TASK_BATCH_SIZE))))
    except (TypeError, ValueError):
        batch_size = DEFAULT_TASK_BATCH_SIZE
    include_level_2 = section.get("include_level_2", legacy_mode != "separated")
    if not isinstance(include_level_2, bool):
        include_level_2 = True
    children_mode = section.get("l2_children_mode", "context" if section.get("include_children_context") else "none")
    if children_mode not in VALID_CHILDREN_MODES:
        children_mode = "none"
    l3_enabled = section.get("l3_loop_enabled", True)
    if not isinstance(l3_enabled, bool):
        l3_enabled = True
    if l3_enabled is False and children_mode == "context":
        # Sem loop L3, os filhos não podem ficar órfãos: o L2 assume a entrega.
        children_mode = "owned"
    if children_mode == "owned":
        l3_enabled = False
    return {
        "mode": mode,
        "batch_size": batch_size,
        "include_level_2": include_level_2,
        "l2_children_mode": children_mode,
        "l3_loop_enabled": l3_enabled,
        "l3_include_parent": bool(section.get("l3_include_parent", True)),
    }


def _development_mode(root: Path) -> str:
    """Retorna a ordem arquitetural do loop de desenvolvimento.

    ``sequential`` preserva o fluxo histórico. ``separated`` executa primeiro
    todas as telas L2 e depois o backend L3, sem exigir testes para as telas.
    Alguns aliases são aceitos para facilitar a migração de configurações
    escritas manualmente.
    """
    config = _get_backlog_config(root)
    configured = config.get("development_mode", config.get("implementation_mode", "sequential"))
    aliases = {
        "separate": "separated",
        "frontend_backend": "separated",
        "frontend-then-backend": "separated",
        "frontend_then_backend": "separated",
        "all": "sequential",
    }
    normalized = aliases.get(str(configured).strip().casefold(), str(configured).strip().casefold())
    return normalized if normalized in VALID_DEVELOPMENT_MODES else "sequential"


def _normalize_task_layer(layer: str | None) -> str | None:
    """Normaliza o filtro opcional de tasks por camada."""
    if layer is None:
        return None
    normalized = str(layer).strip().casefold()
    if normalized in {"", "all", "todas", "todos"}:
        return None
    if normalized not in VALID_TASK_LAYERS:
        raise ValueError("layer deve ser frontend ou backend")
    return normalized


def _layer_matches(task: dict[str, Any], layer: str | None) -> bool:
    """Confirma se uma task pertence à camada solicitada."""
    if layer is None:
        return True
    return ("frontend" if task.get("level") == 2 else "backend" if task.get("level") in {3, 4} else None) == layer


def _test_loop_enabled(root: Path) -> bool:
    """Retorna se o backlog deve executar a fase de testes."""
    configured = _get_backlog_config(root).get("test_loop_enabled", True)
    return configured if isinstance(configured, bool) else True


def _level_guidance(level: str, meaning: str) -> str:
    """Converte a definição escolhida no init em uma orientação acionável."""
    normalized = meaning.casefold().strip()
    if level == "2" and normalized == "tela":
        return "Trate esta task como implementação da view/tela: entregue a apresentação e o comportamento frontend necessário."
    if level == "3" and normalized in {"regra de negócio", "regra de negocio"}:
        return "Trate este fluxo como regra de negócio: implemente decisões, validações, persistência e efeitos exigidos pelo comportamento."
    if level == "3" and normalized == "detalhes da tela":
        return "Trate este fluxo como detalhes da tela: implemente estados, interações, validações e comportamentos específicos da view."
    if level == "3" and normalized in {
        "regra de negócio e detalhes da tela",
        "regra de negocio e detalhes da tela",
    }:
        return "Trate este fluxo como regra de negócio e detalhes da tela: implemente decisões, validações, estados, interações e efeitos necessários."
    if level == "4":
        return "Trate este fluxo como rastreabilidade técnica: ligue o comportamento do L3 a arquivos, módulos, símbolos, contratos, persistência, integrações e testes reais."
    return f"Use esta definição como orientação de escopo para o nível {level}: {meaning}."


def _node_delivery_note() -> str:
    """Explica que a entrega agrupada inclui o nó L2 e seus comportamentos internos."""
    return (
        "Este é um pacote completo: o nó de nível 2 e todos os subfluxos internos listados "
        "fazem parte da mesma entrega. ‘Tela’ classifica o tipo do nó, mas não limita o escopo "
        "ao frontend. Considere todas as camadas exigidas pelo Draw — apresentação, regras, "
        "estados, validações, endpoints/handlers, persistência, hooks, integrações, permissões, "
        "notificações, recuperação e testes — quando estiverem descritas no nó ou nos subfluxos."
    )


def _node_delivery_phase_instruction(phase: str) -> str:
    """Gera a instrução específica do pacote agrupado para cada fase do cursor."""
    if phase == "test":
        return (
            "Na fase de testes, crie cobertura executável para o nó e para todos os subfluxos internos, "
            "incluindo cada camada observável exigida pelo Draw; não teste somente a tela e não implemente produção."
        )
    return (
        "Na fase de implementação, entregue a tela e o funcionamento completo do nó e de todos os subfluxos internos, "
        "incluindo endpoints/handlers, regras, persistência, hooks e integrações quando exigidos pelo Draw; "
        "não deixe essas partes para outra task."
    )


def _level_semantics(root: Path) -> dict[str, dict[str, Any]]:
    """Retorna as definições L2/L3 persistidas e suas orientações para o agente."""
    config = _get_backlog_config(root)
    semantics: dict[str, dict[str, Any]] = {}
    for level, default in DEFAULT_LEVEL_MEANINGS.items():
        configured = config.get(f"level_{level}_meaning", default)
        meaning = configured.strip() if isinstance(configured, str) and configured.strip() else default
        semantics[level] = {
            "level": int(level),
            "meaning": meaning,
            "guidance": _level_guidance(level, meaning),
        }
    return semantics


def _get_backlog_config(root: Path) -> dict[str, Any]:
    """Lê a configuração da chave 'backlog' em .looper/config.json."""
    try:
        data = load_config(root)
        if isinstance(data, dict):
            backlog_cfg = data.get("backlog")
            if isinstance(backlog_cfg, dict):
                return backlog_cfg
    except Exception:
        pass
    return {}


def _bootstrap_enabled(config: dict[str, Any]) -> bool:
    """Habilita bootstrap salvo quando houver opt-out explícito.
    Trata o antigo default ``bootstrap_task: false`` como configuração legada.
    """
    return config.get("bootstrap_opt_out") is not True


def _execution_config(root: Path) -> dict[str, Any]:
    """Normaliza as opções de cursor sem quebrar configurações antigas."""
    config = _get_backlog_config(root)
    size = config.get("task_batch_size", DEFAULT_TASK_BATCH_SIZE)
    try:
        size = max(1, min(5, int(size)))
    except (TypeError, ValueError):
        size = DEFAULT_TASK_BATCH_SIZE
    l4_group_size = config.get("l4_group_size", DEFAULT_L4_GROUP_SIZE)
    try:
        l4_group_size = max(1, min(50, int(l4_group_size)))
    except (TypeError, ValueError):
        l4_group_size = DEFAULT_L4_GROUP_SIZE
    scope = config.get("task_batch_scope", "task")
    if scope not in VALID_TASK_BATCH_SCOPES:
        scope = "task"
    delivery_scope = config.get("task_delivery_scope", config.get("test_task_scope", "task"))
    if delivery_scope not in VALID_TASK_DELIVERY_SCOPES:
        delivery_scope = "task"
    interval = config.get("min_task_interval_seconds", config.get("task_min_interval_seconds", config.get("minimum_task_interval_seconds", DEFAULT_MIN_TASK_INTERVAL_SECONDS)))
    try:
        interval = max(0, int(interval))
    except (TypeError, ValueError):
        interval = DEFAULT_MIN_TASK_INTERVAL_SECONDS
    return {
        "test_loop_enabled": _test_loop_enabled(root),
        "task_batch_size": size,
        "l4_group_size": l4_group_size,
        "task_batch_scope": scope,
        "task_delivery_scope": delivery_scope,
        "development_mode": _development_mode(root),
        "test_loop": _loop_options(root, "test"),
        "implementation_loop": _loop_options(root, "implementation"),
        "min_task_interval_seconds": interval,
        "lease_seconds": max(3, int(config.get("lease_seconds", 900) or 900)),
    }


def get_backlog_config(root: Path) -> dict[str, Any]:
    """Retorna a configuração da seção 'backlog' em .looper/config.json."""
    return _get_backlog_config(root)


def set_backlog_config(
    root: Path,
    verification_interval: int | None = None,
    bootstrap_task: bool | None = None,
    final_verification_task: bool | None = None,
    task_batch_size: int | None = None,
    task_batch_scope: str | None = None,
    task_delivery_scope: str | None = None,
    min_task_interval_seconds: int | None = None,
    level_2_meaning: str | None = None,
    level_3_meaning: str | None = None,
    test_loop_enabled: bool | None = None,
    development_mode: str | None = None,
    test_loop_mode: str | None = None,
    implementation_loop_mode: str | None = None,
    test_batch_size: int | None = None,
    implementation_batch_size: int | None = None,
    l2_children_mode: str | None = None,
    l3_loop_enabled: bool | None = None,
    l3_include_parent: bool | None = None,
    l4_group_size: int | None = None,
) -> dict[str, Any]:
    """Atualiza a seção 'backlog' em .looper/config.json de forma persistente."""
    data: dict[str, Any] = load_config(root)
    backlog_cfg = data.setdefault("backlog", {})
    if not isinstance(backlog_cfg, dict):
        backlog_cfg = {}
        data["backlog"] = backlog_cfg
    if verification_interval is not None:
        backlog_cfg["verification_interval"] = int(verification_interval)
        backlog_cfg["l2_verification_interval"] = int(verification_interval)
    if bootstrap_task is not None:
        backlog_cfg["bootstrap_task"] = bool(bootstrap_task)
        backlog_cfg["bootstrap_opt_out"] = not bool(bootstrap_task)
    if final_verification_task is not None:
        backlog_cfg["final_verification_task"] = bool(final_verification_task)
    if task_batch_size is not None:
        if not 1 <= int(task_batch_size) <= 5:
            raise ValueError("task_batch_size deve estar entre 1 e 5")
        backlog_cfg["task_batch_size"] = int(task_batch_size)
    if task_batch_scope is not None:
        if task_batch_scope not in VALID_TASK_BATCH_SCOPES:
            raise ValueError("task_batch_scope deve ser task ou node")
        backlog_cfg["task_batch_scope"] = task_batch_scope
    if task_delivery_scope is not None:
        if task_delivery_scope not in VALID_TASK_DELIVERY_SCOPES:
            raise ValueError("task_delivery_scope deve ser task ou node")
        backlog_cfg["task_delivery_scope"] = task_delivery_scope
        backlog_cfg.pop("test_task_scope", None)
    if min_task_interval_seconds is not None:
        if int(min_task_interval_seconds) < 0:
            raise ValueError("min_task_interval_seconds não pode ser negativo")
        backlog_cfg["min_task_interval_seconds"] = int(min_task_interval_seconds)
    if test_loop_enabled is not None:
        backlog_cfg["test_loop_enabled"] = bool(test_loop_enabled)
    if development_mode is not None:
        normalized_mode = str(development_mode).strip().casefold()
        aliases = {
            "separate": "separated",
            "frontend_backend": "separated",
            "frontend-then-backend": "separated",
            "frontend_then_backend": "separated",
            "all": "sequential",
        }
        normalized_mode = aliases.get(normalized_mode, normalized_mode)
        if normalized_mode not in VALID_DEVELOPMENT_MODES:
            raise ValueError("development_mode deve ser sequential ou separated")
        backlog_cfg["development_mode"] = normalized_mode
    loop_updates = (
        ("test_loop", test_loop_mode, test_batch_size),
        ("implementation_loop", implementation_loop_mode, implementation_batch_size),
    )
    for section_name, mode, batch_size in loop_updates:
        if mode is not None:
            normalized_loop = _normalize_loop_mode(mode)
            if normalized_loop not in VALID_LOOP_MODES:
                raise ValueError("modo do loop inválido")
            backlog_cfg.setdefault(section_name, {})["mode"] = normalized_loop
        if batch_size is not None:
            if int(batch_size) < 1:
                raise ValueError("batch_size deve ser maior ou igual a 1")
            backlog_cfg.setdefault(section_name, {})["batch_size"] = int(batch_size)
    if l2_children_mode is not None:
        if l2_children_mode not in VALID_CHILDREN_MODES:
            raise ValueError("l2_children_mode deve ser none, context ou owned")
        for section_name in ("test_loop", "implementation_loop"):
            backlog_cfg.setdefault(section_name, {})["l2_children_mode"] = l2_children_mode
    if l3_loop_enabled is not None:
        for section_name in ("test_loop", "implementation_loop"):
            section = backlog_cfg.setdefault(section_name, {})
            section["l3_loop_enabled"] = bool(l3_loop_enabled)
            if not l3_loop_enabled and section.get("l2_children_mode", "none") in {"none", "context"}:
                section["l2_children_mode"] = "owned"
    if l3_include_parent is not None:
        for section_name in ("test_loop", "implementation_loop"):
            backlog_cfg.setdefault(section_name, {})["l3_include_parent"] = bool(l3_include_parent)
    if l4_group_size is not None:
        if not 1 <= int(l4_group_size) <= 50:
            raise ValueError("l4_group_size deve estar entre 1 e 50")
        backlog_cfg["l4_group_size"] = int(l4_group_size)
    for level, meaning in ((2, level_2_meaning), (3, level_3_meaning), (4, None)):
        if meaning is not None:
            normalized = str(meaning).strip()
            if not normalized:
                raise ValueError(f"level_{level}_meaning não pode ser vazio")
            backlog_cfg[f"level_{level}_meaning"] = normalized
    save_config(root, data)
    return backlog_cfg


def _bootstrap_instruction() -> str:
    """Retorna a orientação curta e agnóstica da preparação inicial."""
    return (
        "Prepare o local antes das tasks de produto: leia a estrutura existente e deixe pronto o ponto de entrada, "
        "arquivos raiz, configuração, dependências, convenções e comandos necessários para associar e executar as próximas tasks. "
        "Use as evidências do projeto e da stack; não invente framework nem implemente funcionalidade de produto."
    )


def _verification_requirements() -> list[str]:
    """Retorna o checklist obrigatório da auditoria de implementação."""
    return [
        "Leia o Draw, as decisões respondidas e os subfluxos dos nós auditados.",
        "Localize os arquivos e símbolos reais indicados nas referências de código.",
        "Carregue esses arquivos no contexto e leia o código relevante antes de emitir qualquer conclusão.",
        "Compare o comportamento encontrado com a especificação: tela, regras, estados, validações, persistência, integrações e efeitos reais.",
        "Execute os testes aplicáveis e confirme que o caminho funciona de fato; código presente ou teste superficial não prova implementação.",
        "Só considere implementado o que estiver comprovado no código e funcionando; se faltar, estiver incompleto ou quebrado, relate as evidências e não conclua a task.",
    ]


def _implementation_verification_instruction(labels: list[str]) -> str:
    """Monta a instrução explícita para a auditoria pós-implementação."""
    scope = ", ".join(f"'{label}'" for label in labels)
    checklist = " ".join(requirement for requirement in _verification_requirements())
    return (
        f"Audite obrigatoriamente a implementação dos nós {scope} e de seus subfluxos. "
        "Esta task é uma auditoria real, não uma confirmação automática do status do backlog. "
        f"{checklist} "
        "Não invente arquivos, símbolos, testes ou evidências e não altere o Draw para encobrir uma lacuna."
    )


def _is_verification_task(task: dict[str, Any]) -> bool:
    """Identifica tasks sintéticas de auditoria sem tratá-las como telas."""
    task_id = task.get("id")
    return isinstance(task_id, str) and (task_id.startswith("task:verify:") or task_id == "task:final:verification")


def _create_injected_bootstrap_task() -> dict[str, Any]:
    """Cria a primeira task operacional sem assumir uma stack específica."""
    return {
        "id": "task:bootstrap",
        "draw_id": "system",
        "backlog_id": "system",
        "label": "Preparar a Estrutura Inicial",
        "description": _bootstrap_instruction(),
        "level": 1,
        "status": "in_progress",
        "test_status": "not-required",
        "test_evidence": {"status": "not-required", "reason": "bootstrap inicial"},
        "checklist_state": {"test": True, "implementation": False},
        "branch": {"id": "system:bootstrap", "position": 1},
        "branches": [{"id": "system:bootstrap", "position": 1}],
    }


def bootstrap_report(root: Path) -> dict[str, Any]:
    """Audita os pré-requisitos mínimos antes da primeira task do backlog."""
    documents = _draw_documents(root)
    root_draw = next(
        (document for document in documents if document.get("_hierarchy", {}).get("level") == 1 and document.get("kind") == "system"),
        None,
    )
    from .setup import bootstrap_design_status

    checks = {
        "system_level_1": {"status": "passed" if root_draw else "blocked", "reason": None if root_draw else "system_level_1_missing"},
        "design": bootstrap_design_status(root),
        "env_example": {"status": "passed" if (root / ".env.example").is_file() else "blocked", "reason": None if (root / ".env.example").is_file() else "env_example_missing"},
        "looper_config": {"status": "passed" if (root / ".looper" / "config.yaml").is_file() else "blocked", "reason": None if (root / ".looper" / "config.yaml").is_file() else "config_missing"},
        "draw_storage": {"status": "passed" if (root / ".looper" / "draws" / "index.json").is_file() else "blocked", "reason": None if (root / ".looper" / "draws" / "index.json").is_file() else "draw_storage_missing"},
    }
    failures = [name for name, check in checks.items() if check.get("status") != "passed"]
    return {"status": "blocked" if failures else "passed", "checks": checks, "failures": failures}


def _create_injected_l2_batch_verify_task(target_nodes: list[dict[str, Any]]) -> dict[str, Any]:
    """Cria a task de verificação funcional em lote para 1 ou mais nós L2 finalizados."""
    if not target_nodes:
        raise ValueError("lista de nós vazia para verificação")
    labels = [n.get("label", f"Nó {n.get('node_id')}") for n in target_nodes]
    verification_instruction = _implementation_verification_instruction(labels)
    if len(target_nodes) == 1:
        n = target_nodes[0]
        task_id = f"task:verify:{n.get('draw_id')}:node:{n.get('node_id')}"
        label = f"Verificação da Implementação — {n.get('label', '')}"
        desc = f"Auditoria obrigatória do nó '{n.get('label', '')}' e seus subfluxos. Não declare a implementação com base no status da task: leia os arquivos e símbolos reais, compare o código com o Draw e confirme o funcionamento por evidências."
    else:
        node_ids_str = ":".join(str(n.get("node_id")) for n in target_nodes)
        draw_id = target_nodes[0].get("draw_id", "system")
        task_id = f"task:verify:{draw_id}:batch:{node_ids_str}"
        label = f"Verificação da Implementação em Lote — ({len(target_nodes)} nós: {', '.join(labels)})"
        desc = f"Auditoria obrigatória dos nós ({', '.join(labels)}) e seus subfluxos. Não declare a implementação com base no status das tasks: leia os arquivos e símbolos reais, compare o código com o Draw e confirme o funcionamento por evidências."

    all_symbols: set[str] = set()
    all_deps: set[str] = set()
    all_code_refs: list[dict[str, Any]] = []
    all_questions: list[dict[str, Any]] = []
    all_child_task_ids: list[str] = []
    verified_nodes: list[dict[str, Any]] = []

    for n in target_nodes:
        for s in n.get("symbols", []):
            all_symbols.add(s)
        for d in n.get("source_dependencies", []):
            all_deps.add(d)
        all_code_refs.extend(deepcopy(n.get("code_refs", [])))
        all_questions.extend(deepcopy(n.get("questions", [])))
        all_child_task_ids.extend(n.get("child_task_ids", []))
        verified_nodes.append({
            "task_id": n["id"],
            "draw_id": n.get("draw_id"),
            "node_id": n.get("node_id"),
            "label": n.get("label", ""),
            "description": n.get("description", ""),
            "symbols": list(n.get("symbols", [])),
            "source_dependencies": list(n.get("source_dependencies", [])),
            "code_refs": deepcopy(n.get("code_refs", [])),
            "questions": deepcopy(n.get("questions", [])),
            "child_task_ids": list(n.get("child_task_ids", [])),
        })

    first = target_nodes[0]
    return {
        "id": task_id,
        "draw_id": first.get("draw_id"),
        "backlog_id": first.get("backlog_id"),
        "parent_task_id": first.get("id"),
        "node_id": first.get("node_id"),
        "label": label,
        "description": desc,
        "verification_requirements": _verification_requirements(),
        "verification_instruction": verification_instruction,
        "level": 2,
        "status": "in_progress",
        "verified_nodes": verified_nodes,
        "verified_task_ids": [n["id"] for n in target_nodes],
        "questions": all_questions,
        "code_refs": all_code_refs,
        "symbols": sorted(all_symbols),
        "source_dependencies": sorted(all_deps),
        "child_task_ids": all_child_task_ids,
        "test_status": "not-required",
        "test_evidence": {"status": "not-required", "reason": "verificação em lote de nós L2"},
        "checklist_state": {"test": True, "implementation": False},
        "branch": first.get("branch", {}),
        "branches": first.get("branches", []),
    }


def _create_injected_l2_association_task(target_nodes: list[dict[str, Any]]) -> dict[str, Any]:
    """Cria a segunda auditoria L2: associação de código e testes reais."""
    if not target_nodes:
        raise ValueError("lista de nós vazia para associação")
    first = target_nodes[0]
    ids = ":".join(str(node.get("node_id")) for node in target_nodes)
    draw_id = first.get("draw_id", "system")
    task_id = f"task:associate:{draw_id}:batch:{ids}" if len(target_nodes) > 1 else f"task:associate:{draw_id}:node:{first.get('node_id')}"
    return {
        "id": task_id,
        "draw_id": draw_id,
        "backlog_id": first.get("backlog_id"),
        "parent_task_id": first.get("id"),
        "node_id": first.get("node_id"),
        "label": "Associação de símbolos, arquivos e testes",
        "description": "Associar os símbolos qualificados, arquivos de implementação, views, contratos e testes reais aos nós L2 e aos subfluxos auditados, sem usar placeholders.",
        "level": 2,
        "status": "in_progress",
        "target_task_ids": [node.get("id") for node in target_nodes],
        "verified_nodes": deepcopy([{"node_id": node.get("node_id"), "label": node.get("label", ""), "symbols": node.get("symbols", [])} for node in target_nodes]),
        "test_status": "not-required",
        "test_evidence": {"status": "not-required", "reason": "associação posterior à auditoria funcional"},
        "checklist_state": {"test": True, "implementation": False},
    }


def _create_injected_final_task() -> dict[str, Any]:
    """Cria a task de encerramento final e verificação end-to-end do MVP."""
    verification_instruction = _implementation_verification_instruction(["o MVP completo"])
    return {
        "id": "task:final:verification",
        "draw_id": "system",
        "backlog_id": "system",
        "label": "Verificação Final da Implementação e Associação de Símbolos",
        "description": "Auditoria final obrigatória do MVP completo. Leia os arquivos e símbolos reais, compare o código com a especificação e confirme por evidências que o produto funciona; não declare conclusão apenas porque existem arquivos ou tasks concluídas.",
        "verification_requirements": _verification_requirements(),
        "verification_instruction": verification_instruction,
        "level": 1,
        "status": "in_progress",
        "test_status": "not-required",
        "test_evidence": {"status": "not-required", "reason": "verificação final do MVP"},
        "checklist_state": {"test": True, "implementation": False},
        "branch": {"id": "system:final", "position": 1},
        "branches": [{"id": "system:final", "position": 1}],
    }


def backlog_path(root: Path) -> Path:
    """Retorna o arquivo agregado e persistente do backlog do projeto."""
    return root / ".looper" / "backlog.json"


def _atomic_write(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def _draw_documents(root: Path) -> list[dict[str, Any]]:
    """Carrega os Draws indexados em ordem hierárquica estável."""
    index_path = draw_directory(root) / "index.json"
    if index_path.exists():
        entries = read_draw_index(root).get("draws", [])
        draw_ids = [entry.get("id") for entry in entries if isinstance(entry, dict) and isinstance(entry.get("id"), str)]
    else:
        draw_ids = [path.stem for path in sorted(draw_directory(root).glob("*.json")) if path.name != "index.json"]
    documents = []
    for draw_id in draw_ids:
        try:
            document = read_draw(root, draw_id)
        except ValueError:
            continue
        hierarchy = document.get("hierarchy") if isinstance(document.get("hierarchy"), dict) else {}
        documents.append(document | {"_hierarchy": hierarchy})
    return sorted(
        documents,
        key=lambda document: (
            int(document["_hierarchy"].get("level", 99)),
            str(document["_hierarchy"].get("parent_draw_ref") or ""),
            str(document.get("id", "")),
        ),
    )


def _reference_symbols(node: dict[str, Any]) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    """Extrai símbolos, dependências e referências sem inventar fatos."""
    symbols: set[str] = set()
    dependencies: set[str] = set()
    references: list[dict[str, Any]] = []
    for reference in node.get("code_refs", []):
        if isinstance(reference, str):
            reference = {"symbol": reference}
        if not isinstance(reference, dict):
            continue
        symbol = reference.get("symbol") or reference.get("qualified_name")
        if isinstance(symbol, str) and symbol.strip():
            symbols.add(symbol.strip())
        source_dependencies = reference.get("source_dependencies", [])
        if isinstance(source_dependencies, list):
            dependencies.update(item.strip() for item in source_dependencies if isinstance(item, str) and item.strip())
        references.append(deepcopy(reference))
    return sorted(symbols), sorted(dependencies), references


def _normalize_test_ref(node: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Normaliza test_ref/test_refs para um arquivo e funções de teste.
    Aceita os dois formatos públicos, mas rejeita cobertura espalhada por arquivos.
    """
    raw_refs: list[Any] = []
    if "test_ref" in node:
        raw_refs.append(node.get("test_ref"))
    if "test_refs" in node:
        raw_value = node.get("test_refs")
        if not isinstance(raw_value, list):
            return None, "test_refs deve ser uma lista"
        raw_refs.extend(raw_value)
    if not raw_refs:
        return None, "test_ref ausente"

    files: set[str] = set()
    symbols: set[str] = set()
    for reference in raw_refs:
        if not isinstance(reference, dict):
            return None, "cada referência de teste deve ser um objeto"
        file = reference.get("file")
        if not isinstance(file, str) or not file.strip():
            return None, "referência de teste precisa de file"
        files.add(file.strip())
        raw_symbols = reference.get("symbols")
        if not isinstance(raw_symbols, list):
            return None, "referência de teste precisa de symbols como lista"
        symbols.update(symbol.strip() for symbol in raw_symbols if isinstance(symbol, str) and symbol.strip())
    if len(files) != 1:
        return None, "a cobertura de teste deve usar um único arquivo"
    if not symbols:
        return None, "referência de teste precisa de ao menos uma função em symbols"
    return {"file": next(iter(files)), "symbols": sorted(symbols)}, None


def _static_test_symbols(root: Path) -> list[dict[str, Any]] | None:
    """Lê o inventário de símbolos produzido pela análise estática atual."""
    path = root / ".looper" / "adapters" / "static-analysis-kpis.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    details = payload.get("details") if isinstance(payload, dict) else None
    symbols = details.get("symbols") if isinstance(details, dict) else None
    return symbols if isinstance(symbols, list) else None


def _test_reference_status(root: Path, test_ref: dict[str, Any] | None, error: str | None = None) -> dict[str, Any]:
    """Comprova arquivo e funções de teste sem afirmar cobertura não analisada."""
    if error or test_ref is None:
        return {"status": "missing", "file": test_ref.get("file") if test_ref else None, "symbols": test_ref.get("symbols", []) if test_ref else [], "reason": error or "test_ref ausente"}
    file_value = test_ref["file"]
    file_path = Path(file_value)
    if file_path.is_absolute() or ".." in file_path.parts:
        return {"status": "missing", **deepcopy(test_ref), "reason": "arquivo de teste precisa ser relativo ao projeto"}
    if not (root / file_path).is_file():
        return {"status": "missing", **deepcopy(test_ref), "reason": "arquivo de teste não existe"}
    available = _static_test_symbols(root)
    if available is None:
        return {"status": "missing", **deepcopy(test_ref), "reason": "análise estática de testes não disponível"}
    available_symbols = {
        (item.get("qualified_name"), item.get("file"))
        for item in available
        if isinstance(item, dict)
    }
    missing = [symbol for symbol in test_ref["symbols"] if (symbol, file_value) not in available_symbols]
    if missing:
        return {"status": "missing", **deepcopy(test_ref), "missing_symbols": missing, "reason": "função(ões) de teste não encontrada(s) na análise estática"}
    return {"status": "done", **deepcopy(test_ref), "missing_symbols": [], "reason": "arquivo e funções comprovados"}


def _default_checklist_state(task: dict[str, Any]) -> dict[str, bool]:
    """Cria os estados de checklist para backlogs antigos ou tasks novas."""
    return {
        "test": task.get("test_status") in {"done", "not-required"},
        "implementation": task.get("status") == "done",
    }


def _task_test_complete(task: dict[str, Any]) -> bool:
    """Confirma teste executado ou liberado manualmente no viewer."""
    state = task.get("checklist_state", {})
    return state.get("test") is True and (
        task.get("test_status") == "done" or task.get("test_manual") is True
    )


def _valid_checklist_state(value: Any) -> dict[str, bool] | None:
    """Aceita somente os dois marcadores booleanos persistidos pelo viewer."""
    if not isinstance(value, dict):
        return None
    if not isinstance(value.get("test"), bool) or not isinstance(value.get("implementation"), bool):
        return None
    return {"test": value["test"], "implementation": value["implementation"]}


def _traceability(root: Path, draw_id: str, node_id: Any, symbols: list[str]) -> list[dict[str, Any]]:
    """Acrescenta o status factual dos símbolos já analisados."""
    facts_path = facts_directory(root) / f"{draw_id}.facts.json"
    if not facts_path.exists():
        return [{"symbol": symbol, "status": "not-analyzed"} for symbol in symbols]
    try:
        facts = json.loads(facts_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [{"symbol": symbol, "status": "not-analyzed"} for symbol in symbols]
    node_facts = facts.get("nodes", {}).get(str(node_id), {}) if isinstance(facts, dict) else {}
    fact_references = node_facts.get("references", []) if isinstance(node_facts, dict) else []
    by_symbol = {
        item.get("symbol"): item
        for item in fact_references
        if isinstance(item, dict) and isinstance(item.get("symbol"), str)
    }
    return [
        {"symbol": symbol, **{key: value for key, value in by_symbol.get(symbol, {}).items() if key != "symbol"}}
        if symbol in by_symbol
        else {"symbol": symbol, "status": "not-analyzed"}
        for symbol in symbols
    ]


def _child_checklist_id(node: dict[str, Any], checklist_ids: set[str]) -> str | None:
    """Retorna somente uma referência de subfluxo que exista no backlog."""
    child_id = node.get("draw_ref")
    return child_id if isinstance(child_id, str) and child_id in checklist_ids else None


def _checklist_item(root: Path, document: dict[str, Any], node: dict[str, Any], checklist_ids: set[str]) -> dict[str, Any]:
    """Monta o item informativo de qualquer nó, em qualquer nível."""
    symbols, dependencies, code_refs = _reference_symbols(node)
    return {
        "id": f"item:{document['id']}:node:{node['id']}",
        "node_id": node["id"],
        "label": node.get("label", ""),
        "description": node.get("description", ""),
        "status": "pending",
        "questions": deepcopy(node.get("questions", [])) if isinstance(node.get("questions", []), list) else [],
        "code_refs": code_refs,
        "symbols": symbols,
        "source_dependencies": dependencies,
        "traceability": _traceability(root, str(document["id"]), node["id"], symbols),
        "child_checklist_id": _child_checklist_id(node, checklist_ids),
    }


def _has_self_loop(document: dict[str, Any], node_id: Any) -> bool:
    return any(
        isinstance(edge, dict) and edge.get("from") == node_id and edge.get("to") == node_id
        for edge in document.get("edges", [])
    )


def _graph_branches(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Enumera caminhos simples e encerra self-loops sem recursão infinita."""
    nodes = [node.get("id") for node in document.get("nodes", []) if isinstance(node, dict)]
    edges = [edge for edge in document.get("edges", []) if isinstance(edge, dict)]
    outgoing: dict[Any, list[dict[str, Any]]] = {node_id: [] for node_id in nodes}
    incoming: dict[Any, int] = {node_id: 0 for node_id in nodes}
    for edge in edges:
        if edge.get("from") not in outgoing or edge.get("to") not in outgoing:
            continue
        outgoing[edge["from"]].append(edge)
        if edge["from"] != edge["to"]:
            incoming[edge["to"]] += 1
    for edge_list in outgoing.values():
        edge_list.sort(key=lambda edge: (int(edge.get("id", 0)), str(edge.get("label", ""))))
    roots = sorted((node_id for node_id, count in incoming.items() if count == 0), key=str) or sorted(nodes, key=str)
    branches: list[dict[str, Any]] = []

    def walk(path: list[Any], branch_edges: list[dict[str, Any]], branch_number: list[int], visited: set[Any]) -> None:
        current = path[-1]
        continuations = outgoing.get(current, [])
        if not continuations:
            branches.append({"id": branch_number[0], "node_ids": path, "edges": branch_edges, "terminal_node_id": current, "terminal_reason": "no-outgoing"})
            branch_number[0] += 1
            return
        for edge in continuations:
            target = edge.get("to")
            next_edges = branch_edges + [edge]
            if target == current:
                branches.append({"id": branch_number[0], "node_ids": path, "edges": next_edges, "terminal_node_id": current, "terminal_reason": "self-loop"})
                branch_number[0] += 1
            elif target in visited:
                branches.append({"id": branch_number[0], "node_ids": path + [target], "edges": next_edges, "terminal_node_id": target, "terminal_reason": "cycle"})
                branch_number[0] += 1
            else:
                walk(path + [target], next_edges, branch_number, visited | {target})

    for root_node in roots:
        walk([root_node], [], [len(branches) + 1], {root_node})
    return branches


def _branches_for_draw(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Prefere caminhos explícitos e garante uma branch para cada nó."""
    flows = [flow for flow in document.get("flows", []) if isinstance(flow, dict) and flow.get("steps")]
    if not flows:
        return _graph_branches(document)
    branches = []
    for index, flow in enumerate(flows, start=1):
        node_ids = [step.get("node") for step in flow.get("steps", []) if isinstance(step, dict)]
        if not node_ids:
            continue
        terminal = node_ids[-1]
        reason = "self-loop" if _has_self_loop(document, terminal) else "flow-end"
        branches.append({"id": index, "node_ids": node_ids, "edges": [], "terminal_node_id": terminal, "terminal_reason": reason, "flow_id": flow.get("id")})
    covered_node_ids = {
        node_id
        for branch in branches
        for node_id in branch.get("node_ids", [])
    }
    next_branch_id = max((int(branch["id"]) for branch in branches), default=0) + 1
    for node in document.get("nodes", []):
        if not isinstance(node, dict) or node.get("id") in covered_node_ids:
            continue
        node_id = node.get("id")
        branches.append({
            "id": next_branch_id,
            "node_ids": [node_id],
            "edges": [],
            "terminal_node_id": node_id,
            "terminal_reason": "node-not-listed-in-flow",
            "flow_id": None,
        })
        next_branch_id += 1
    return branches


def _existing_state(root: Path) -> dict[str, Any]:
    path = backlog_path(root)
    if not path.exists():
        return {}
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return document if isinstance(document, dict) else {}


def _branch_occurrence(draw_id: str, branch: dict[str, Any], position: int, node_id: Any) -> dict[str, Any]:
    """Descreve uma ocorrência de nó dentro de uma branch específica."""
    return {
        "id": f"{draw_id}:branch:{branch['id']}",
        "position": position,
        "terminal": node_id == branch.get("terminal_node_id"),
        "terminal_node_id": branch.get("terminal_node_id"),
        "terminal_reason": branch.get("terminal_reason"),
    }


def _task_for_node(root: Path, document: dict[str, Any], node: dict[str, Any], branch: dict[str, Any], position: int, checklist_ids: set[str], parent_task_id: str | None = None, test_owner_task_id: str | None = None) -> dict[str, Any]:
    draw_id = str(document["id"])
    node_id = node["id"]
    symbols, dependencies, code_refs = _reference_symbols(node)
    level = document.get("_hierarchy", {}).get("level")
    item_id = f"task:{draw_id}:node:{node_id}"
    occurrence = _branch_occurrence(draw_id, branch, position, node_id)
    test_ref, test_ref_error = _normalize_test_ref(node) if level == 2 else (None, None)
    owner_id = item_id if level == 2 else test_owner_task_id
    return {
        "id": item_id,
        "draw_id": draw_id,
        "backlog_id": draw_id,
        "parent_task_id": parent_task_id,
        "draw_title": document.get("title", draw_id),
        "node_id": node_id,
        "level": level,
        "label": node.get("label", ""),
        "description": node.get("description", ""),
        "questions": deepcopy(node.get("questions", [])) if isinstance(node.get("questions", []), list) else [],
        "code_refs": code_refs,
        "symbols": symbols,
        "source_dependencies": dependencies,
        "traceability": _traceability(root, draw_id, node_id, symbols),
        "test_ref": test_ref,
        "test_ref_error": test_ref_error,
        "test_owner_task_id": owner_id,
        "test_status": "missing" if owner_id else "not-required",
        "test_evidence": _test_reference_status(root, test_ref, test_ref_error) if level == 2 else {"status": "missing", "reason": "teste próprio do subfluxo ainda não concluído"},
        "checklist_state": {"test": False, "implementation": False},
        "child_checklist_id": next((ref for ref in node.get("draw_ref", []) if ref in checklist_ids), node.get("draw_ref")) if isinstance(node.get("draw_ref"), list) else node.get("draw_ref"),
        "status": "pending",
        "branch": occurrence,
        "branches": [occurrence],
    }


def _refresh_branch_completion(payload: dict[str, Any]) -> None:
    """Recalcula todas as branches a partir do status das suas tasks."""
    tasks_by_id = {
        task.get("id"): task
        for task in payload.get("tasks", [])
        if isinstance(task, dict) and isinstance(task.get("id"), str)
    }
    completed_branches = []
    execution = payload.get("execution", {})
    for branch in execution.get("branches", []):
        task_ids = branch.get("task_ids", [])
        branch["completed"] = bool(task_ids) and all(
            tasks_by_id.get(task_id, {}).get("status") == "done"
            for task_id in task_ids
        )
        if branch["completed"]:
            completed_branches.append(branch["id"])
    execution["completed_branches"] = completed_branches


def _append_child_backlog(root: Path, parent_task: dict[str, Any], parent_node: dict[str, Any], context: dict[str, Any]) -> None:
    """Expande recursivamente o backlog associado ao nó pai."""
    child_id = parent_node.get("draw_ref")
    documents_by_id = context["documents_by_id"]
    child_document = documents_by_id.get(str(child_id)) if isinstance(child_id, str) else None
    expanded = context["expanded_child_backlogs"]
    if child_document is None or str(child_id) in expanded:
        return
    hierarchy = child_document.get("_hierarchy", {})
    if hierarchy.get("parent_draw_ref") != parent_task.get("draw_id") or hierarchy.get("parent_node_id") != parent_task.get("node_id"):
        return
    expanded.add(str(child_id))
    child_nodes = {node.get("id"): node for node in child_document.get("nodes", []) if isinstance(node, dict)}
    child_task_ids: list[str] = []
    child_branch_ids: list[str] = []
    for child_branch in _branches_for_draw(child_document):
        branch_task_ids: list[str] = []
        branch_node_ids: list[Any] = []
        for position, node_id in enumerate(child_branch["node_ids"], start=1):
            child_node = child_nodes.get(node_id)
            if child_node is None:
                continue
            task_id = f"task:{child_id}:node:{node_id}"
            tasks_by_id = context["tasks_by_id"]
            child_task = tasks_by_id.get(task_id)
            if child_task is None:
                child_task = _task_for_node(
                    root,
                    child_document,
                    child_node,
                    child_branch,
                    position,
                    context["checklist_ids"],
                    parent_task["id"],
                    parent_task.get("test_owner_task_id"),
                )
                previous_task = context["previous_tasks"].get(task_id)
                if previous_task and previous_task.get("status") in VALID_TASK_STATUSES:
                    child_task["status"] = previous_task["status"]
                context["tasks"].append(child_task)
                tasks_by_id[task_id] = child_task
                _append_child_backlog(root, child_task, child_node, context)
            else:
                occurrence = _branch_occurrence(str(child_id), child_branch, position, node_id)
                if not any(item.get("id") == occurrence["id"] for item in child_task.get("branches", [])):
                    child_task.setdefault("branches", []).append(occurrence)
            branch_node_ids.append(node_id)
            branch_task_ids.append(task_id)
            descendants = child_task.get("child_task_ids", [])
            for descendant_id in descendants:
                if descendant_id not in branch_task_ids:
                    branch_task_ids.append(descendant_id)
            for nested_task_id in [task_id, *descendants]:
                if nested_task_id not in child_task_ids:
                    child_task_ids.append(nested_task_id)
        branch_id = f"{child_id}:branch:{child_branch['id']}"
        child_branch_ids.append(branch_id)
        context["execution_branches"].append({
            "id": branch_id,
            "draw_id": str(child_id),
            "backlog_id": str(child_id),
            "parent_task_id": parent_task["id"],
            "flow_id": child_branch.get("flow_id"),
            "task_ids": branch_task_ids,
            "node_ids": branch_node_ids,
            "edges": deepcopy(child_branch.get("edges", [])),
            "terminal_node_id": child_branch.get("terminal_node_id"),
            "terminal_reason": child_branch.get("terminal_reason"),
            "scope": "nested",
            "completed": False,
        })
    parent_task["child_backlog_id"] = str(child_id)
    parent_task["child_task_ids"] = child_task_ids
    parent_task["child_branch_ids"] = child_branch_ids


def _build_checklist(root: Path, document: dict[str, Any], checklist_ids: set[str], context: dict[str, Any]) -> dict[str, Any]:
    """Constrói o checklist e as branches operacionais de um Draw."""
    draw_id = str(document["id"])
    hierarchy = deepcopy(document.get("_hierarchy", {}))
    nodes_by_id = {node.get("id"): node for node in document.get("nodes", []) if isinstance(node, dict)}
    items = [_checklist_item(root, document, node, checklist_ids) for node in nodes_by_id.values()]
    items_by_node = {item["node_id"]: item for item in items}
    if hierarchy.get("level") != 2:
        return {
            "id": draw_id,
            "draw_id": draw_id,
            "title": document.get("title", draw_id),
            "hierarchy": hierarchy,
            "parent_checklist_id": hierarchy.get("parent_draw_ref"),
            "parent_node_id": hierarchy.get("parent_node_id"),
            "items": items,
        }
    for branch in _branches_for_draw(document):
        branch_task_ids = []
        branch_node_ids = []
        for position, node_id in enumerate(branch["node_ids"], start=1):
            if node_id not in nodes_by_id:
                continue
            task_id = f"task:{draw_id}:node:{node_id}"
            branch_task_ids.append(task_id)
            branch_node_ids.append(node_id)
            task = context["tasks_by_id"].get(task_id)
            if task is None:
                task = _task_for_node(root, document, nodes_by_id[node_id], branch, position, checklist_ids)
                previous_task = context["previous_tasks"].get(task_id)
                if previous_task and previous_task.get("status") in VALID_TASK_STATUSES:
                    task["status"] = previous_task["status"]
                context["tasks"].append(task)
                context["tasks_by_id"][task_id] = task
                items_by_node[node_id].update({"task_id": task_id, "status": task["status"], "task": task})
            else:
                occurrence = _branch_occurrence(draw_id, branch, position, node_id)
                if not any(item.get("id") == occurrence["id"] for item in task.get("branches", [])):
                    task.setdefault("branches", []).append(occurrence)
            _append_child_backlog(root, task, nodes_by_id[node_id], context)
            for child_task_id in task.get("child_task_ids", []):
                if child_task_id not in branch_task_ids:
                    branch_task_ids.append(child_task_id)
        context["execution_branches"].append({
            "id": f"{draw_id}:branch:{branch['id']}",
            "draw_id": draw_id,
            "backlog_id": draw_id,
            "flow_id": branch.get("flow_id"),
            "task_ids": branch_task_ids,
            "node_ids": branch_node_ids,
            "edges": deepcopy(branch.get("edges", [])),
            "terminal_node_id": branch.get("terminal_node_id"),
            "terminal_reason": branch.get("terminal_reason"),
            "scope": "root",
            "completed": False,
        })
    return {
        "id": draw_id,
        "draw_id": draw_id,
        "title": document.get("title", draw_id),
        "hierarchy": hierarchy,
        "parent_checklist_id": hierarchy.get("parent_draw_ref"),
        "parent_node_id": hierarchy.get("parent_node_id"),
        "items": items,
    }


def _refresh_test_statuses(
    root: Path,
    tasks: list[dict[str, Any]],
    previous_tasks: dict[str, dict[str, Any]] | None = None,
) -> None:
    """Atualiza testes; subfluxos só herdam o L2 no modo agrupado."""
    previous_tasks = previous_tasks or {}
    if not _test_loop_enabled(root):
        for task in tasks:
            task["test_status"] = "not-required"
            task["test_evidence"] = {
                "status": "not-required",
                "reason": "loop de testes desabilitado no looper init",
            }
        return
    delivery_scope = _execution_config(root)["task_delivery_scope"]
    separated = _development_mode(root) == "separated"
    owners = {
        task["id"]: task
        for task in tasks
        if task.get("level") == 2
    }
    for task in owners.values():
        if separated:
            task["test_status"] = "not-required"
            task["test_evidence"] = {
                "status": "not-required",
                "reason": "modo separado: telas L2 não entram no loop de testes",
            }
            task["test_ref"] = None
            task["test_ref_error"] = None
            continue
        reference, error = _normalize_test_ref(task)
        error = task.get("test_ref_error") or error
        evidence = _test_reference_status(root, reference, error)
        task["test_ref"] = reference
        task["test_ref_error"] = error
        task["test_status"] = evidence["status"]
        task["test_evidence"] = evidence
        previous = previous_tasks.get(task["id"], {})
        if evidence["status"] == "missing" and previous.get("test_status") == "done":
            task["test_status"] = "done"
            task["test_evidence"] = {
                "status": "done",
                "reason": "fase de testes concluída anteriormente",
            }
    for task in tasks:
        owner_id = task.get("test_owner_task_id")
        if task.get("level") == 2 or not owner_id:
            continue
        previous = previous_tasks.get(task["id"], {})
        if separated or delivery_scope == "task":
            # Em entregas separadas, um L3 não pode ser liberado só porque o
            # teste do L2 foi concluído. Preserve apenas conclusões que já
            # pertenciam ao próprio L3 (sem a referência herdada do L2).
            task["test_ref"] = None
            task["test_ref_error"] = None
            if (
                previous.get("test_status") == "done"
                and previous.get("test_completed_independently") is True
            ) or previous.get("test_manual") is True:
                task["test_status"] = "done"
                task["test_manual"] = True
                task["test_evidence"] = {"status": "done", "reason": "fase de testes concluída anteriormente"}
            else:
                task["test_status"] = "missing"
                task["test_evidence"] = {"status": "missing", "reason": "teste próprio do subfluxo ainda não concluído"}
            continue
        owner = owners.get(owner_id)
        if owner is None:
            task["test_status"] = "missing"
            task["test_evidence"] = {"status": "missing", "reason": "task proprietária de teste não encontrada"}
            continue
        task["test_ref"] = deepcopy(owner.get("test_ref"))
        task["test_status"] = owner.get("test_status", "missing")
        task["test_evidence"] = deepcopy(owner.get("test_evidence", {}))


def _refresh_checklist_states(tasks: list[dict[str, Any]], previous_tasks: dict[str, dict[str, Any]]) -> None:
    """Preserva marcações manuais e inicializa o estado dos subfluxos."""
    owners = {task["id"]: task for task in tasks if task.get("level") == 2}
    for task in tasks:
        previous = previous_tasks.get(task.get("id"), {})
        state = _valid_checklist_state(previous.get("checklist_state"))
        if state is None:
            state = _default_checklist_state(task)
            owner = owners.get(task.get("test_owner_task_id"))
            if task.get("level") != 2 and owner is not None:
                state["test"] = _valid_checklist_state(owner.get("checklist_state")) is not None and owner["checklist_state"]["test"]
        task["checklist_state"] = state
        if task.get("test_status") == "not-required":
            task["checklist_state"]["test"] = True
        if task.get("level") == 2 and task.get("test_evidence", {}).get("reason", "").startswith("modo separado"):
            task["checklist_state"]["test"] = True
        if task.get("level") != 2 and task.get("test_status") == "missing" and not task.get("test_manual"):
            task["checklist_state"]["test"] = False
        if previous.get("test_manual") is True:
            task["test_manual"] = True


def _phase_checklists(tasks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Materializa os dois checklists centrais a partir das tasks atuais."""
    result = {"test": [], "implementation": []}
    for task in tasks:
        state = task.get("checklist_state", {})
        base = {
            "task_id": task["id"],
            "draw_id": task.get("draw_id"),
            "node_id": task.get("node_id"),
            "label": task.get("label", ""),
            "parent_task_id": task.get("parent_task_id"),
        }
        result["test"].append({"id": f"check:test:{task['id']}", **base, "checked": bool(state.get("test")), "evidence_status": task.get("test_evidence", {}).get("status")})
        result["implementation"].append({"id": f"check:implementation:{task['id']}", **base, "checked": bool(state.get("implementation")), "status": task.get("status")})
    return result


def build_backlog(root: Path, generated_at: str | None = None) -> dict[str, Any]:
    """Constrói o backlog único, preservando progresso e cursor anteriores."""
    documents = _draw_documents(root)
    previous = _existing_state(root)
    previous_tasks = {item.get("id"): item for item in previous.get("tasks", []) if isinstance(item, dict) and isinstance(item.get("id"), str)}
    checklist_ids = {str(document["id"]) for document in documents}
    documents_by_id = {str(document["id"]): document for document in documents}
    checklists = []
    tasks = []
    tasks_by_id: dict[str, dict[str, Any]] = {}
    execution_branches = []
    context = {
        "documents_by_id": documents_by_id,
        "expanded_child_backlogs": set(),
        "tasks_by_id": tasks_by_id,
        "tasks": tasks,
        "previous_tasks": previous_tasks,
        "checklist_ids": checklist_ids,
        "execution_branches": execution_branches,
    }

    checklists = [_build_checklist(root, document, checklist_ids, context) for document in documents]
    _refresh_test_statuses(root, tasks, previous_tasks)
    _refresh_checklist_states(tasks, previous_tasks)
    previous_execution = previous.get("execution", {}) if isinstance(previous.get("execution", {}), dict) else {}
    execution_config = _execution_config(root)
    current_phase = previous_execution.get("current_phase")
    valid_task_ids = {task["id"] for task in tasks}
    prev_id = previous_execution.get("current_task_id")
    is_injected_id = bool(prev_id and (
        prev_id == "task:bootstrap"
        or prev_id.startswith("task:verify:")
        or prev_id == "task:final:verification"
        or prev_id.startswith("change:")
    ))
    current_task_id = prev_id if (prev_id in valid_task_ids or is_injected_id) else None
    if not _test_loop_enabled(root) and current_phase == "test":
        current = next((task for task in tasks if task["id"] == current_task_id), None)
        if current is not None and current.get("status") == "in_progress":
            previous_status = current.pop("test_previous_status", None)
            current["status"] = previous_status if previous_status in VALID_TASK_STATUSES else "pending"
        current_task_id = None
        current_phase = None
    if current_task_id and current_phase != "test" and not is_injected_id and next((task for task in tasks if task["id"] == current_task_id), {}).get("status") == "done":
        current_task_id = None
    current_task = next((task for task in tasks if task["id"] == current_task_id), None)
    for checklist in checklists:
        for item in checklist.get("items", []):
            task_id = f"task:{checklist['draw_id']}:node:{item['node_id']}"
            task = tasks_by_id.get(task_id)
            if task is not None:
                item.update({"task_id": task_id, "status": task["status"], "task": task})
    backlogs = []
    for document in documents:
        draw_id = str(document["id"])
        draw_tasks = [task for task in tasks if task.get("backlog_id") == draw_id]
        if not draw_tasks:
            continue
        backlogs.append({
            "id": f"backlog:{draw_id}",
            "draw_id": draw_id,
            "title": document.get("title", draw_id),
            "parent_task_id": next((task.get("parent_task_id") for task in draw_tasks if task.get("parent_task_id")), None),
            "task_ids": [task["id"] for task in draw_tasks],
        })
    payload = {
        "version": BACKLOG_VERSION,
        "kind": "backlog",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "system": {"root_draw_ids": [str(document["id"]) for document in documents if document.get("_hierarchy", {}).get("level") == 1]},
        "level_semantics": _level_semantics(root),
        "checklists": checklists,
        "phase_checklists": _phase_checklists(tasks),
        "backlogs": backlogs,
        "tasks": tasks,
        "execution": {
            "current_task_id": current_task_id,
            "lanes": deepcopy(previous_execution.get("lanes", {})) if isinstance(previous_execution.get("lanes", {}), dict) else {},
            "current_backlog_id": current_task.get("backlog_id") if current_task else previous_execution.get("current_backlog_id"),
            "current_branch_id": previous_execution.get("current_branch_id"),
            "branch_position": previous_execution.get("branch_position"),
            "current_phase": current_phase,
            "test_loop_enabled": execution_config["test_loop_enabled"],
            "current_parent_task_id": previous_execution.get("current_parent_task_id"),
            "current_subtask_id": previous_execution.get("current_subtask_id"),
            "current_l4_group_task_ids": previous_execution.get("current_l4_group_task_ids"),
            "bootstrap_done": previous_execution.get("bootstrap_done", False),
            "verified_l2_task_ids": previous_execution.get("verified_l2_task_ids", []),
            "current_verified_batch_node_ids": previous_execution.get("current_verified_batch_node_ids", []),
            "current_association_node_ids": previous_execution.get("current_association_node_ids", []),
            "final_verification_done": previous_execution.get("final_verification_done", False),
            "lease_id": previous_execution.get("lease_id"),
            "lease_started_at": previous_execution.get("lease_started_at"),
            "lease_expires_at": previous_execution.get("lease_expires_at"),
            "last_claim_at": previous_execution.get("last_claim_at"),
            "last_transition_at": previous_execution.get("last_transition_at"),
            "lease_seconds": execution_config["lease_seconds"],
            "task_batch_size": execution_config["task_batch_size"],
            "l4_group_size": execution_config["l4_group_size"],
            "task_batch_scope": execution_config["task_batch_scope"],
            "task_delivery_scope": execution_config["task_delivery_scope"],
            "development_mode": execution_config["development_mode"],
            "test_loop": execution_config["test_loop"],
            "implementation_loop": execution_config["implementation_loop"],
            "completed_branches": [],
            "branches": execution_branches,
        },
    }
    _refresh_branch_completion(payload)
    return payload


def validate_backlog(payload: Any) -> list[str]:
    """Valida o contrato mínimo antes de persistir um backlog."""
    if not isinstance(payload, dict):
        return ["backlog deve ser um objeto"]
    violations = []
    if payload.get("version") != BACKLOG_VERSION:
        violations.append("version de backlog inválida")
    if payload.get("kind") != "backlog":
        violations.append("kind de backlog inválido")
    if not isinstance(payload.get("tasks"), list):
        violations.append("tasks deve ser uma lista")
    else:
        for index, task in enumerate(payload["tasks"]):
            if not isinstance(task, dict) or not isinstance(task.get("id"), str):
                violations.append(f"tasks[{index}] precisa de id")
            elif task.get("status") not in VALID_TASK_STATUSES:
                violations.append(f"tasks[{index}].status inválido")
            if isinstance(task, dict):
                test_status = task.get("test_status")
                if test_status is not None and test_status not in VALID_TEST_STATUSES | {"not-required"}:
                    violations.append(f"tasks[{index}].test_status inválido")
                test_ref = task.get("test_ref")
                if test_ref is not None:
                    if not isinstance(test_ref, dict):
                        violations.append(f"tasks[{index}].test_ref deve ser um objeto")
                    else:
                        if not isinstance(test_ref.get("file"), str) or not test_ref["file"].strip():
                            violations.append(f"tasks[{index}].test_ref.file é obrigatório")
                        symbols = test_ref.get("symbols")
                        if not isinstance(symbols, list) or not all(isinstance(symbol, str) and symbol.strip() for symbol in symbols):
                            violations.append(f"tasks[{index}].test_ref.symbols deve ser uma lista de nomes")
                checklist_state = task.get("checklist_state")
                if checklist_state is not None and _valid_checklist_state(checklist_state) is None:
                    violations.append(f"tasks[{index}].checklist_state inválido")
    if not isinstance(payload.get("execution"), dict):
        violations.append("execution deve ser um objeto")
    elif payload["execution"].get("current_phase") not in VALID_EXECUTION_PHASES:
        violations.append("execution.current_phase inválido")
    phase_checklists = payload.get("phase_checklists")
    if phase_checklists is not None:
        if not isinstance(phase_checklists, dict):
            violations.append("phase_checklists deve ser um objeto")
        else:
            for phase in VALID_CHECKLIST_PHASES:
                if not isinstance(phase_checklists.get(phase), list):
                    violations.append(f"phase_checklists.{phase} deve ser uma lista")
    return violations


def write_backlog(root: Path, payload: dict[str, Any]) -> Path:
    """Valida e grava o backlog agregado de forma atômica."""
    violations = validate_backlog(payload)
    if violations:
        raise ValueError("Backlog inválido: " + "; ".join(violations))
    return _atomic_write(backlog_path(root), payload)


def read_backlog(root: Path) -> dict[str, Any]:
    """Lê o backlog persistido e rejeita documentos incompatíveis."""
    path = backlog_path(root)
    if not path.exists():
        raise ValueError("backlog ainda não foi gerado")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("backlog inválido") from error
    violations = validate_backlog(payload)
    if violations:
        raise ValueError("Backlog inválido: " + "; ".join(violations))
    return payload


def check_backlog(root: Path) -> dict[str, Any]:
    """Verifica se o backlog persistido não deixou implementação sem check.
    Ausência de backlog não bloqueia projetos que ainda não adotaram o fluxo.
    """
    path = backlog_path(root)
    if not path.exists():
        return {
            "name": "backlog",
            "status": "not_executed",
            "reason": "backlog_not_generated",
            "total": 0,
            "done": 0,
            "remaining": 0,
            "missing_tests": 0,
            "missing_test_task_ids": [],
            "current_task_id": None,
        }
    try:
        payload = read_backlog(root)
    except ValueError as error:
        return {
            "name": "backlog",
            "status": "blocked",
            "reason": "backlog_invalid",
            "total": 0,
            "done": 0,
            "remaining": 0,
            "missing_tests": 0,
            "missing_test_task_ids": [],
            "current_task_id": None,
            "errors": [str(error)],
        }
    tasks = [task for task in payload.get("tasks", []) if isinstance(task, dict)]
    remaining = [task for task in tasks if task.get("status") != "done"]
    execution = payload.get("execution", {}) if isinstance(payload.get("execution"), dict) else {}
    config = _get_backlog_config(root)
    tests_enabled = _test_loop_enabled(root)
    missing_tests = _pending_test_tasks(payload) if tests_enabled else []
    blocked_by_tests = bool(missing_tests)
    bootstrap_pending = bool(tasks and _bootstrap_enabled(config) and not execution.get("bootstrap_done", False))
    final_pending = bool(tasks and config.get("final_verification_task", config.get("final_verification_enabled", False)) and not execution.get("final_verification_done", False))
    
    interval = config.get("verification_interval", config.get("l2_verification_interval", 0))
    verify_pending = False
    if interval > 0:
        tasks_by_id = {t.get("id"): t for t in tasks}
        if payload.get("execution", {}).get("development_mode") == "separated":
            l3_tasks = [t for t in tasks if t.get("level") == 3]
            verified_ids = set(execution.get("verified_l3_task_ids", execution.get("verified_l2_task_ids", [])))
            completed_l3 = [t for t in l3_tasks if t.get("status") == "done"]
            unverified = [t for t in completed_l3 if t.get("id") not in verified_ids]
            if unverified and (len(unverified) >= interval or not remaining):
                verify_pending = True
        else:
            l2_tasks = [t for t in tasks if t.get("level") == 2]
            verified_ids = set(execution.get("verified_l2_task_ids", []))
            completed_l2 = [
                t for t in l2_tasks
                if t.get("status") == "done" and all(tasks_by_id.get(cid, {}).get("status") == "done" for cid in t.get("child_task_ids", []))
            ]
            unverified = [t for t in completed_l2 if t.get("id") not in verified_ids]
            if unverified and (len(unverified) >= interval or not remaining):
                verify_pending = True

    injected_pending_count = (1 if bootstrap_pending else 0) + (1 if final_pending else 0) + (1 if verify_pending else 0)
    has_pending = bool(remaining or blocked_by_tests or injected_pending_count > 0)

    return {
        "name": "backlog",
        "status": "blocked" if has_pending else "passed",
        "reason": "tasks_missing_tests" if blocked_by_tests else "tasks_pending" if has_pending else "all_tasks_complete",
        "total": len(tasks),
        "done": len(tasks) - len(remaining),
        "remaining": len(remaining) + injected_pending_count,
        "remaining_task_ids": [task.get("id") for task in remaining[:10]],
        "missing_tests": len(missing_tests),
        "missing_test_task_ids": [task.get("id") for task in missing_tests[:10]],
        "test_loop_enabled": tests_enabled,
        "current_task_id": execution.get("current_task_id"),
    }


def generate_backlog(root: Path) -> dict[str, Any]:
    """Reconstrói a estrutura sem perder os status já persistidos."""
    payload = build_backlog(root)
    write_backlog(root, payload)
    return payload


def missing_backlog(root: Path) -> dict[str, Any]:
    """Retorna somente tasks que ainda não estão concluídas."""
    payload = generate_backlog(root)
    items = [deepcopy(task) for task in payload["tasks"] if task.get("status") != "done"]
    done = len(payload["tasks"]) - len(items)
    return {
        "kind": "missing-backlog",
        "version": BACKLOG_VERSION,
        "summary": {"total": len(payload["tasks"]), "missing": len(items), "done": done},
        "items": items,
    }


def _change_task_id(draw_id: str, node_id: int, change_id: int) -> str:
    return f"change:{draw_id}:node:{node_id}:request:{change_id}"


def _find_change_requests(root: Path) -> list[dict[str, Any]]:
    """Localiza pedidos de alteração persistidos nos nós dos Draws."""
    requests: list[dict[str, Any]] = []
    for entry in read_draw_index(root).get("draws", []):
        draw_id = entry.get("id") if isinstance(entry, dict) else None
        if not isinstance(draw_id, str):
            continue
        document = read_draw(root, draw_id)
        for node in document.get("nodes", []):
            if not isinstance(node, dict) or not isinstance(node.get("id"), int):
                continue
            for change in node.get("changes", []):
                if not isinstance(change, dict) or not isinstance(change.get("id"), int):
                    continue
                status = change.get("status", "pending")
                if status not in {"pending", "in_progress"}:
                    continue
                symbols, dependencies, references = _reference_symbols(node)
                hierarchy = document.get("_hierarchy", document.get("hierarchy", {}))
                level = hierarchy.get("level") if isinstance(hierarchy, dict) else None
                requests.append({
                    "id": _change_task_id(draw_id, node["id"], change["id"]),
                    "draw_id": draw_id,
                    "draw_title": document.get("title", draw_id),
                    "node_id": node["id"],
                    "level": level,
                    "implementation_layer": "frontend" if level == 2 else "backend" if level == 3 else None,
                    "label": f"Alteração: {node.get('label', node['id'])}",
                    "description": change.get("prompt", ""),
                    "change_id": change["id"],
                    "status": status,
                    "questions": deepcopy(node.get("questions", [])),
                    "symbols": symbols,
                    "code_refs": references,
                    "source_dependencies": dependencies,
                })
    return requests


def _change_context(change: dict[str, Any], kind: str = "backlog-change-task", critical_information: str = "") -> dict[str, Any]:
    """Formata o pedido de alteração como task independente do backlog normal."""
    instruction = (
        "Implemente este pedido de alteração no nó e em todos os locais necessários da codebase. "
        "Leia os símbolos e testes associados, crie ou ajuste regressões quando necessário, execute os gates e só então conclua a alteração."
    )
    return {
        "kind": kind,
        "phase": "change",
        "status": "in_progress" if kind == "backlog-change-task" else "done",
        "task": change,
        "instruction": _with_critical_instruction(instruction, critical_information),
        "critical_information": {
            "file": CRITICAL_INFORMATION_FILE,
            "content": critical_information,
            "present": bool(critical_information),
        },
        "remaining": None,
    }


def next_backlog_change(root: Path, layer: str | None = None) -> dict[str, Any]:
    """Reserva um pedido de alteração do Draw sem bloquear os loops de teste e task."""
    layer = _normalize_task_layer(layer)
    payload = generate_backlog(root)
    execution = payload["execution"]
    current_id = execution.get("current_task_id")
    requests = _find_change_requests(root)
    if execution.get("current_phase") == "change" and isinstance(current_id, str):
        current = next((request for request in requests if request["id"] == current_id), None)
        if current is not None:
            if layer is not None and current.get("implementation_layer") != layer:
                raise ValueError(f"a alteração atual pertence à camada {current.get('implementation_layer')}; conclua-a antes de pedir somente {layer}")
            return _change_context(current, critical_information=_critical_information(root))
        _clear_execution_cursor(execution)

    if execution.get("current_task_id"):
        raise ValueError("há uma task de backlog em andamento; conclua-a antes de reservar uma alteração")
    request = next((item for item in requests if item.get("status") == "pending" and _layer_matches(item, layer)), None)
    if request is None:
        write_backlog(root, payload)
        if layer is not None:
            return {"kind": "backlog-layer-empty", "phase": "change", "status": "complete", "layer": layer, "remaining": 0}
        return {"kind": "backlog-change-empty", "phase": "change", "status": "complete", "remaining": 0}

    document = read_draw(root, request["draw_id"])
    for node in document.get("nodes", []):
        if node.get("id") != request["node_id"]:
            continue
        for change in node.get("changes", []):
            if change.get("id") == request["change_id"]:
                change["status"] = "in_progress"
                break
    create_draw(root, document)
    request["status"] = "in_progress"
    execution["current_task_id"] = request["id"]
    execution["current_phase"] = "change"
    execution["current_backlog_id"] = request["draw_id"]
    execution["current_branch_id"] = None
    execution["branch_position"] = None
    execution["current_parent_task_id"] = None
    execution["current_subtask_id"] = None
    _mark_claim(execution)
    write_backlog(root, payload)
    return _change_context(request, critical_information=_critical_information(root))


def _clear_execution_cursor(execution: dict[str, Any]) -> None:
    """Limpa a reserva atual sem apagar o histórico das branches."""
    execution["current_task_id"] = None
    execution["current_backlog_id"] = None
    execution["current_branch_id"] = None
    execution["branch_position"] = None
    execution["current_phase"] = None
    execution["current_parent_task_id"] = None
    execution["current_subtask_id"] = None
    execution["current_l4_group_task_ids"] = None
    execution["lease_id"] = None
    execution["lease_started_at"] = None
    execution["lease_expires_at"] = None
    execution["last_transition_at"] = datetime.now(timezone.utc).isoformat()


def _mark_claim(execution: dict[str, Any]) -> None:
    """Registra lease/cursor de uma reserva sem esconder o histórico."""
    now = datetime.now(timezone.utc)
    lease_seconds = int(execution.get("lease_seconds", 900) or 900)
    execution["lease_id"] = f"lease:{now.timestamp():.6f}"
    execution["lease_started_at"] = now.isoformat()
    execution["lease_expires_at"] = (now.timestamp() + lease_seconds)
    execution["last_claim_at"] = now.isoformat()


def _enforce_claim_window(execution: dict[str, Any], config: dict[str, Any]) -> None:
    """Bloqueia somente avanço rápido configurado; reler a task atual é seguro."""
    minimum = int(config.get("min_task_interval_seconds", 0) or 0)
    previous = execution.get("last_transition_at")
    if minimum <= 0 or not isinstance(previous, str):
        return
    try:
        elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(previous)).total_seconds()
    except ValueError:
        return
    if elapsed < minimum:
        raise ValueError(f"janela mínima entre tasks ainda não terminou ({minimum} segundos)")


def _parent_task(tasks: list[dict[str, Any]], task: dict[str, Any]) -> dict[str, Any]:
    """Encontra a task pai raiz que contextualiza uma subtask."""
    by_id = {item.get("id"): item for item in tasks}
    current = task
    visited: set[str] = set()
    while isinstance(current.get("parent_task_id"), str) and current["parent_task_id"] not in visited:
        visited.add(current["id"])
        parent = by_id.get(current["parent_task_id"])
        if parent is None:
            break
        current = parent
    return current


def _navigation_action(label: Any, condition_label: str) -> str:
    """Retorna o rótulo da ação sem repetir a condição da conexão."""
    text = str(label or "").strip()
    if not text:
        return ""
    normalized = text.casefold()
    for prefix in (f"{condition_label}:", f"{condition_label} ", f"{condition_label},"):
        if normalized.startswith(prefix.casefold()):
            return text[len(prefix):].strip()
    return text


def _draw_navigation_context(root: Path, draw_id: Any, node_id: Any, task_label: str) -> dict[str, Any]:
    """Monta as entradas de navegação de um nó sem escolher uma única origem."""
    context: dict[str, Any] = {
        "origin_nodes": [],
        "origin_edges": [],
        "access_paths": [],
        "navigation_entries": [],
        "previous_node": None,
        "connection": None,
    }
    if draw_id is None or node_id is None:
        return context
    try:
        document = read_draw(root, draw_id)
        nodes = {node.get("id"): node for node in document.get("nodes", [])}
        target_node = nodes.get(node_id)
        for edge in document.get("edges", []):
            if edge.get("to") != node_id:
                continue
            context["origin_edges"].append(edge)
            from_id = edge.get("from")
            from_node = nodes.get(from_id)
            if from_node is None:
                continue
            context["origin_nodes"].append(from_node)
            label = from_node.get("label") or str(from_id)
            condition = EDGE_CONDITIONS.get(edge.get("condition"), "então")
            action = _navigation_action(edge.get("label"), condition)
            context["access_paths"].append(f"Nó {label} → {condition} → Nó atual")
            context["navigation_entries"].append({
                "origin": {
                    "node_id": from_id,
                    "label": from_node.get("label", ""),
                    "description": from_node.get("description", ""),
                },
                "target": {
                    "node_id": node_id,
                    "label": (target_node or {}).get("label", task_label),
                },
                "condition": edge.get("condition"),
                "condition_label": condition,
                "action": action,
                "label": edge.get("label", ""),
                "description": edge.get("description", ""),
            })
            if context["previous_node"] is None:
                context["previous_node"] = {
                    "node_id": from_id,
                    "label": from_node.get("label", ""),
                    "description": from_node.get("description", ""),
                    "questions": deepcopy(from_node.get("questions", [])),
                    "symbols": _reference_symbols(from_node)[0],
                }
                context["connection"] = {
                    "condition": edge.get("condition"),
                    "condition_label": condition,
                    "label": edge.get("label", ""),
                    "description": edge.get("description", ""),
                }
    except Exception:
        pass
    return context


def _task_context(root: Path, payload: dict[str, Any], task: dict[str, Any], phase: str, kind: str, instruction: str | None = None) -> dict[str, Any]:
    """Retorna a task atual com pai e subtasks para o agente manter contexto."""
    tasks = payload.get("tasks", [])
    parent = _parent_task(tasks, task)
    descendants = [
        item for item in tasks
        if item.get("id") in parent.get("child_task_ids", [])
    ]
    subtask = task if task.get("id") != parent.get("id") else next(
        (item for item in descendants if item.get("status") != "done"),
        None,
    )
    
    draw_id = task.get("backlog_id")
    node_id = task.get("node_id")
    verification_task = _is_verification_task(task)
    navigation = (
        {"origin_nodes": [], "origin_edges": [], "access_paths": [], "navigation_entries": [], "previous_node": None, "connection": None}
        if verification_task
        else _draw_navigation_context(root, draw_id, node_id, task.get("label", ""))
    )

    navigation_target: dict[str, Any] | None = None
    if node_id is not None and not verification_task:
        navigation_target = {
            "node_id": node_id,
            "label": task.get("label", ""),
            "kind": "screen" if task.get("level") == 2 else "step",
        }
        if task.get("level") != 2 and parent.get("level") == 2:
            navigation_target["screen_label"] = parent.get("label", "")
            navigation_target["screen_node_id"] = parent.get("node_id")

    if phase == "bootstrap":
        state = "bootstrap_in_progress"
    elif phase == "test":
        state = "tests_in_progress"
    elif task.get("test_status") in {"missing", "in_progress"}:
        state = "tests_missing"
    elif task.get("status") == "in_progress":
        state = "implementation_in_progress"
    elif task.get("status") == "done":
        state = "backlog_complete" if not any(item.get("status") != "done" for item in tasks) else "tests_ready"
    else:
        state = "tests_ready"

    is_first_l3_for_screen = False
    parent_screen_context: dict[str, Any] | None = None
    if task.get("level") == 3 and parent.get("level") == 2:
        if descendants and descendants[0].get("id") == task.get("id"):
            is_first_l3_for_screen = True
            parent_draw_id = parent.get("draw_id")
            parent_node_id = parent.get("node_id")
            parent_nav = _draw_navigation_context(root, parent_draw_id, parent_node_id, parent.get("label", ""))
            parent_screen_context = {
                "id": parent.get("id"),
                "node_id": parent_node_id,
                "label": parent.get("label", ""),
                "description": parent.get("description", ""),
                "draw_title": parent.get("draw_title") or parent.get("draw_id"),
                "symbols": list(parent.get("symbols", [])),
                "questions": deepcopy(parent.get("questions", [])),
                "navigation_entries": parent_nav.get("navigation_entries", []),
                "access_paths": parent_nav.get("access_paths", []),
            }

    l3_parent = _l3_parent_task(payload, task)
    l4_group = _l4_group_tasks(payload, task)

    development_mode = payload.get("execution", {}).get("development_mode", "sequential")
    subtasks_list = [] if (development_mode == "separated" and task.get("level") == 2) else descendants
    response: dict[str, Any] = {
        "kind": kind,
        "phase": phase,
        "state": state,
        "task": task,
        "parent_task": parent,
        "subtask": subtask,
        "subtasks": subtasks_list,
        "origin_nodes": navigation["origin_nodes"],
        "origin_edges": navigation["origin_edges"],
        "access_paths": navigation["access_paths"],
        "navigation_target": navigation_target,
        "navigation_entries": navigation["navigation_entries"],
        "previous_node": navigation["previous_node"],
        "connection": navigation["connection"],
        "condition": navigation["connection"].get("condition_label") if navigation["connection"] else None,
        "path": navigation["access_paths"][0] if navigation["access_paths"] else None,
        "is_first_l3_for_screen": is_first_l3_for_screen,
        "parent_screen_context": parent_screen_context,
    }
    if l3_parent is not None:
        response["l4_parent"] = deepcopy(l3_parent)
        response["l4_group"] = deepcopy(l4_group)
        response["l4_group_size"] = len(l4_group)
        response["l4_delivery_note"] = (
            "Entregue o pai L3 junto com este grupo de nós L4. "
            "Valide e implemente todos os nós do grupo nesta mesma interação."
        )
    loop_options = payload.get("execution", {}).get("test_loop" if phase == "test" else "implementation_loop", {})
    if not isinstance(loop_options, dict):
        loop_options = {}
    children_mode = loop_options.get("l2_children_mode", "none")
    if task.get("level") == 2 and descendants and children_mode in {"context", "owned"}:
        response["children_delivery_mode"] = children_mode
        response["children_context"] = deepcopy(descendants)
        response["context_only"] = children_mode == "context"
        response["owned_child_task_ids"] = [item.get("id") for item in descendants] if children_mode == "owned" else []
        response["l3_loop_enabled"] = bool(loop_options.get("l3_loop_enabled", True))
        response["instruction"] = (
            f"{response.get('instruction', '').rstrip()} "
            + ("Os L3 abaixo são somente contexto; o loop L3 continua responsável por eles."
               if children_mode == "context" else
               "Os L3 abaixo fazem parte desta entrega e serão concluídos com o L2; não há loop L3 nesta fase.")
        ).strip()
    if task.get("level") == 3 and loop_options.get("l3_include_parent", True) and parent.get("level") == 2:
        response["context_parent"] = deepcopy(parent)
        response["context_only"] = True
        response["parent_context_injected"] = True
    delivery_scope = _task_delivery_scope(payload)
    is_node_delivery = delivery_scope == "node" and task.get("level") == 2 and task.get("id") == parent.get("id")
    node_delivery_note = _node_delivery_note() if is_node_delivery else None
    if is_node_delivery:
        phase_instruction = _node_delivery_phase_instruction(phase)
        instruction = f"{instruction.rstrip()} {phase_instruction}" if instruction else phase_instruction

    level_context = payload.get("level_semantics", {}).get(str(task.get("level"))) if isinstance(payload.get("level_semantics"), dict) else None
    if isinstance(level_context, dict):
        response["level_context"] = deepcopy(level_context)
        if is_node_delivery:
            response["level_context"]["guidance"] = node_delivery_note
    if development_mode == "separated" and task.get("level") in {2, 3, 4}:
        if task.get("level") == 2:
            response["implementation_layer"] = "frontend"
            response["tests_required"] = False
            response["level_context"] = {
                "level": 2,
                "meaning": "Frontend / view",
                "guidance": "Fase frontend: implemente a view/tela, seus estados visuais, interações e a navegação/links entre telas descritos no fluxo. Deixe controller, model, regras de negócio, persistência e integrações para a fase backend L3.",
            }
            if phase == "implementation":
                instruction = f"{instruction.rstrip()} " if instruction else ""
                instruction += "Fase frontend: construa a tela/view, os estados e o link/navegação para as telas de destino descritos no Draw; não implemente controller, model, regra de negócio, persistência ou backend."
        else:
            response["implementation_layer"] = "backend"
            response["tests_required"] = True
            response["level_context"] = {
                "level": task.get("level"),
                "meaning": "Backend / controller, model e codebase L4" if task.get("level") == 4 else "Backend / controller e model",
                "guidance": "Fase backend: implemente a ligação técnica de baixo nível do L4 aos arquivos, símbolos, contratos, persistência e testes reais." if task.get("level") == 4 else "Fase backend: implemente controller, model, regras, persistência e integrações necessárias para o comportamento do L3.",
            }
            if phase == "test":
                instruction = f"{instruction.rstrip()} " if instruction else ""
                instruction += "Fase backend: crie testes para os contratos e símbolos deste L4; não crie testes de tela." if task.get("level") == 4 else "Fase backend: crie testes para controller, model e regras deste L3; não crie testes de tela."
            elif phase == "implementation":
                instruction = f"{instruction.rstrip()} " if instruction else ""
                instruction += "Fase backend: implemente o detalhamento técnico deste L4 e sua rastreabilidade na codebase; a regra L3 e a tela já foram tratadas." if task.get("level") == 4 else "Fase backend: implemente controller, model e o comportamento funcional deste L3; a tela já foi tratada na fase frontend."
    response["task_delivery_scope"] = delivery_scope
    response["development_mode"] = development_mode
    if response["task_delivery_scope"] == "node" and task.get("id") == parent.get("id"):
        response["delivery_subtasks"] = deepcopy(descendants)
    if node_delivery_note:
        response["delivery_scope_note"] = node_delivery_note
    options = _execution_config(root)
    allow_batch = (development_mode != "separated" or task.get("level") == 3)
    if allow_batch and options["task_batch_size"] > 1 and task.get("id") in [item.get("id") for item in tasks]:
        start = next(index for index, item in enumerate(tasks) if item.get("id") == task.get("id"))
        candidates = [
            item for item in tasks[start:]
            if item.get("status") != "done" and (development_mode != "separated" or item.get("level") == 3)
        ]
        if options["task_batch_scope"] == "node":
            candidates = [item for item in candidates if item.get("node_id") == task.get("node_id")]
        if len(candidates) > 1:
            response["batch"] = [{"id": item.get("id"), "label": item.get("label", "")} for item in candidates[:options["task_batch_size"]]]
            response["batch_size"] = len(response["batch"])
    critical_information = _critical_information(root)
    response["critical_information"] = {
        "file": CRITICAL_INFORMATION_FILE,
        "content": critical_information,
        "present": bool(critical_information),
    }
    instruction = instruction if instruction is not None else response.get("instruction")
    instruction = _with_critical_instruction(instruction, critical_information)
    if instruction is not None:
        response["instruction"] = instruction
    return response


def _task_for_update(payload: dict[str, Any], task_id: str) -> dict[str, Any]:
    """Obtém uma task do backlog ou retorna um erro acionável."""
    task = next((item for item in payload.get("tasks", []) if item.get("id") == task_id), None)
    if task is None:
        raise ValueError("task-id não existe no backlog")
    return task


def _l3_parent_task(payload: dict[str, Any], task: dict[str, Any]) -> dict[str, Any] | None:
    """Retorna o L3 que possui diretamente a task L4."""
    tasks = payload.get("tasks", [])
    if task.get("level") == 3:
        return task
    if task.get("level") != 4:
        return None
    by_id = {item.get("id"): item for item in tasks}
    parent = by_id.get(task.get("parent_task_id"))
    return parent if isinstance(parent, dict) and parent.get("level") == 3 else None


def _l4_group_tasks(payload: dict[str, Any], task: dict[str, Any], include_done: bool = False) -> list[dict[str, Any]]:
    """Seleciona um grupo estável de L4 diretos do L3 atual."""
    parent = _l3_parent_task(payload, task)
    if parent is None:
        return []
    tasks_by_id = {item.get("id"): item for item in payload.get("tasks", [])}
    children = [
        tasks_by_id[item_id]
        for item_id in parent.get("child_task_ids", [])
        if item_id in tasks_by_id and tasks_by_id[item_id].get("level") == 4
    ]
    if not include_done:
        children = [item for item in children if item.get("status") != "done"]
    group_size = payload.get("execution", {}).get("l4_group_size", DEFAULT_L4_GROUP_SIZE)
    try:
        group_size = max(1, int(group_size))
    except (TypeError, ValueError):
        group_size = DEFAULT_L4_GROUP_SIZE
    if task.get("level") == 4:
        ids = [item.get("id") for item in children]
        try:
            start = ids.index(task.get("id"))
        except ValueError:
            start = 0
        return children[start:start + group_size]
    return children[:group_size]


def _l4_delivery_tasks(payload: dict[str, Any], task: dict[str, Any]) -> list[dict[str, Any]]:
    """Retorna o L3 e o grupo L4 que devem ser tratados na mesma entrega."""
    parent = _l3_parent_task(payload, task)
    if parent is None:
        return [task]
    group = _l4_group_tasks(payload, task)
    result = [parent] if parent.get("status") != "done" else []
    if task.get("id") != parent.get("id") and task.get("status") != "done" and task not in result:
        result.append(task)
    result.extend(item for item in group if item not in result)
    return result or [task]


def _test_scope_tasks(payload: dict[str, Any], task: dict[str, Any]) -> list[dict[str, Any]]:
    """Retorna o pai e todos os subfluxos cobertos pelo teste agregado."""
    if task.get("level") in {3, 4} and _l3_parent_task(payload, task) is not None:
        return _l4_delivery_tasks(payload, task)
    parent = _parent_task(payload.get("tasks", []), task)
    return [parent] + [
        item for item in payload.get("tasks", [])
        if item.get("id") in parent.get("child_task_ids", [])
    ]


def _task_delivery_scope(payload: dict[str, Any]) -> str:
    """Retorna o escopo comum de entrega das fases de teste e implementação."""
    if payload.get("execution", {}).get("development_mode") == "separated":
        # A separação por camada não pode agrupar L2 e L3 no mesmo pacote,
        # mesmo que uma configuração antiga tenha task_delivery_scope=node.
        return "task"
    scope = payload.get("execution", {}).get("task_delivery_scope")
    if scope not in VALID_TASK_DELIVERY_SCOPES:
        scope = payload.get("execution", {}).get("test_task_scope", "task")
    return scope if scope in VALID_TASK_DELIVERY_SCOPES else "task"


def _phase_loop_options(payload: dict[str, Any], phase: str) -> dict[str, Any]:
    """Retorna a política persistida para a fase atual."""
    value = payload.get("execution", {}).get("test_loop" if phase == "test" else "implementation_loop", {})
    return value if isinstance(value, dict) else {}


def _test_scope_complete(payload: dict[str, Any], task: dict[str, Any]) -> bool:
    """Verifica evidência e marcação de teste para pai e todos os subfluxos."""
    if payload.get("execution", {}).get("test_loop_enabled", True) is False:
        return True
    if task.get("level") in {3, 4} and _l3_parent_task(payload, task) is not None:
        return all(_task_test_complete(item) for item in _test_scope_tasks(payload, task))
    options = _phase_loop_options(payload, "test")
    if task.get("level") == 2 and options.get("l2_children_mode") == "owned":
        return all(_task_test_complete(item) for item in _test_scope_tasks(payload, task))
    if payload.get("execution", {}).get("development_mode") == "separated":
        return task.get("level") != 3 or _task_test_complete(task)
    if _task_delivery_scope(payload) == "task":
        return _task_test_complete(task)
    scope = _test_scope_tasks(payload, task)
    return all(_task_test_complete(item) for item in scope)


def _pending_test_tasks(payload: dict[str, Any], layer: str | None = None) -> list[dict[str, Any]]:
    """Retorna as tasks que ainda precisam passar pela fase de testes."""
    layer = _normalize_task_layer(layer)
    if payload.get("execution", {}).get("test_loop_enabled", True) is False:
        return []
    options = _phase_loop_options(payload, "test")
    if layer == "frontend" and options.get("include_level_2") is False:
        return []
    if layer == "backend" and options.get("l3_loop_enabled") is False:
        return []
    if layer is not None:
        return [
            item for item in payload.get("tasks", [])
            if _layer_matches(item, layer) and not _task_test_complete(item)
        ]
    if options.get("l3_loop_enabled") is False:
        return [
            item for item in payload.get("tasks", [])
            if item.get("level") == 2 and options.get("include_level_2", True) and not _test_scope_complete(payload, item)
        ]
    if options.get("include_level_2") is False:
        return [
            item for item in payload.get("tasks", [])
            if item.get("level") in {3, 4} and not _task_test_complete(item)
        ]
    if _task_delivery_scope(payload) == "task":
        return [
            item for item in payload.get("tasks", [])
            if item.get("level") in {2, 3, 4} and not _test_scope_complete(payload, item)
        ]
    return [
        item for item in payload.get("tasks", [])
        if item.get("level") == 2 and not _test_scope_complete(payload, item)
    ]


def _implementation_delivery_task(payload: dict[str, Any], task: dict[str, Any], layer: str | None = None) -> dict[str, Any]:
    """Agrupa subfluxos na task pai quando o escopo de entrega é `node`."""
    if layer is not None or payload.get("execution", {}).get("development_mode") == "separated":
        return task
    if _task_delivery_scope(payload) != "node" or _phase_loop_options(payload, "implementation").get("l2_children_mode") == "context":
        return task
    parent = _parent_task(payload.get("tasks", []), task)
    return parent if parent.get("status") != "done" else task


def _next_implementation_task(payload: dict[str, Any], layer: str | None = None) -> dict[str, Any] | None:
    """Escolhe a próxima task respeitando a ordem arquitetural configurada."""
    layer = _normalize_task_layer(layer)
    pending = [
        item for item in payload.get("tasks", [])
        if item.get("status") != "done" and _layer_matches(item, layer)
    ]
    options = _phase_loop_options(payload, "implementation")
    if options.get("l3_loop_enabled") is False:
        pending = [item for item in pending if item.get("level") != 3]
    if layer is not None:
        return pending[0] if pending else None
    if payload.get("execution", {}).get("development_mode") != "separated":
        return pending[0] if pending else None
    screens = [item for item in pending if item.get("level") == 2]
    if screens:
        return screens[0]
    return next((item for item in pending if item.get("level") in {3, 4}), None)


def _refresh_task_checklist_items(payload: dict[str, Any]) -> None:
    """Sincroniza checklist, task status e branches depois de uma edição."""
    payload["phase_checklists"] = _phase_checklists(payload.get("tasks", []))
    for checklist in payload.get("checklists", []):
        for item in checklist.get("items", []):
            task = next((task for task in payload.get("tasks", []) if task.get("id") == item.get("task_id")), None)
            if task is not None:
                item["status"] = task.get("status", "pending")
                item["task"] = task
    _refresh_branch_completion(payload)


def update_backlog_checklist(root: Path, task_id: str, phase: str, checked: bool) -> dict[str, Any]:
    """Atualiza um checkbox do backlog pela API local do viewer."""
    if phase not in VALID_CHECKLIST_PHASES:
        raise ValueError("fase de checklist inválida")
    if not isinstance(checked, bool):
        raise ValueError("checked deve ser booleano")
    payload = generate_backlog(root)
    task = _task_for_update(payload, task_id)
    state = task.setdefault("checklist_state", _default_checklist_state(task))
    if phase == "implementation" and checked and not _test_scope_complete(payload, task):
        raise ValueError("checklist de teste do nó e dos subfluxos ainda não foi concluído")
    state[phase] = checked
    if phase == "test":
        if checked:
            task["test_manual"] = True
        else:
            task.pop("test_manual", None)
    if phase == "implementation":
        task["status"] = "done" if checked else "pending"
    elif not checked:
        parent = _parent_task(payload.get("tasks", []), task)
        scope_ids = {parent.get("id"), *parent.get("child_task_ids", [])}
        for item in payload.get("tasks", []):
            if item.get("id") in scope_ids:
                item.setdefault("checklist_state", _default_checklist_state(item))["implementation"] = False
                item["status"] = "pending"
    _refresh_task_checklist_items(payload)
    write_backlog(root, payload)
    return {"kind": "backlog-checklist-updated", "phase": phase, "checked": checked, "task": task, "backlog": payload}


def next_backlog_test(root: Path, layer: str | None = None) -> dict[str, Any]:
    """Entrega a próxima task de teste antes da implementação.
    Mantém a reserva incremental e agrega os subfluxos na task de nível 2.
    """
    layer = _normalize_task_layer(layer)
    payload = generate_backlog(root)
    if not _test_loop_enabled(root):
        return {
            "kind": "backlog-test-disabled",
            "phase": "test",
            "status": "disabled",
            "instruction": "O loop de testes está desabilitado no looper init; use looper backlog task para executar somente implementação.",
        }
    execution = _lane_execution(payload["execution"], "test", layer)
    current_id = execution.get("current_task_id")
    current = next((task for task in payload["tasks"] if task["id"] == current_id), None)
    if layer is not None and current is not None and not _layer_matches(current, layer):
        current_layer = "frontend" if current.get("level") == 2 else "backend"
        raise ValueError(f"a task atual pertence à camada {current_layer}; conclua-a antes de pedir somente {layer}")
    if current_id == "task:bootstrap":
        return _task_context(root, payload, _create_injected_bootstrap_task(), "bootstrap", "backlog-bootstrap-task", _bootstrap_instruction())

    # Um backlog gerado por uma versão anterior pode ter uma task de produto
    # reservada antes do bootstrap, deixando `bootstrap_done` falso e o cursor
    # na fase de testes. O bootstrap é uma barreira global e precisa recuperar
    # esse estado antes de devolver a task antiga.
    config = _get_backlog_config(root)
    bootstrap_enabled = _bootstrap_enabled(config)
    if payload["tasks"] and bootstrap_enabled and not execution.get("bootstrap_done", False):
        if current is not None:
            previous_status = current.pop("test_previous_status", None)
            if previous_status in VALID_TASK_STATUSES:
                current["status"] = previous_status
            elif current.get("status") == "in_progress":
                current["status"] = "pending"
            if current.get("test_status") == "in_progress":
                current["test_status"] = "missing"
        execution["current_task_id"] = None
        execution["current_backlog_id"] = None
        execution["current_branch_id"] = None
        execution["branch_position"] = None
        execution["current_parent_task_id"] = None
        execution["current_subtask_id"] = None
        execution["lease_id"] = None
        execution["lease_started_at"] = None
        execution["lease_expires_at"] = None
        task = _create_injected_bootstrap_task()
        task["checks"] = bootstrap_report(root)
        execution["current_task_id"] = task["id"]
        _mark_claim(execution)
        execution["current_backlog_id"] = "system"
        execution["current_phase"] = "bootstrap"
        write_backlog(root, payload)
        return _task_context(root, payload, task, "bootstrap", "backlog-bootstrap-task", _bootstrap_instruction())

    if execution.get("current_phase") == "test" and current is not None:
        return _task_context(root, payload, current, "test", "backlog-test-task")
    if execution.get("current_phase") in {"bootstrap", "implementation"} and current is not None:
        raise ValueError("a task atual já está na fase de implementação")
    task = next(iter(_pending_test_tasks(payload, layer)), None)
    if task is None:
        _clear_execution_cursor(execution)
        write_backlog(root, payload)
        if layer is not None:
            return {"kind": "backlog-layer-empty", "phase": "test", "status": "complete", "layer": layer, "remaining": 0}
        return {"kind": "backlog-test-empty", "status": "complete", "remaining": 0}
    task["test_status"] = "in_progress"
    task["test_previous_status"] = task.get("status")
    if task.get("status") == "pending":
        task["status"] = "in_progress"
    execution["current_task_id"] = task["id"]
    _mark_claim(execution)
    execution["current_backlog_id"] = task.get("backlog_id")
    execution["current_branch_id"] = task.get("branch", {}).get("id")
    execution["branch_position"] = task.get("branch", {}).get("position")
    execution["current_phase"] = "test"
    execution["current_parent_task_id"] = _parent_task(payload["tasks"], task).get("id")
    execution["current_subtask_id"] = task.get("id") if task.get("parent_task_id") else None
    execution["current_l4_group_task_ids"] = [item["id"] for item in _l4_group_tasks(payload, task)] or None
    write_backlog(root, payload)
    return _task_context(root, payload,
        task,
        "test",
        "backlog-test-task",
        (
            "Crie os testes deste nó ou subfluxo; não implemente produção."
            if _task_delivery_scope(payload) == "task"
            else "Crie os testes do nó de nível 2 e de todos os seus subfluxos; não implemente produção."
        ),
    )


def next_backlog_task(root: Path, verification_interval: int | None = None, layer: str | None = None) -> dict[str, Any]:
    """Entrega e persiste a próxima task da ordem de branches."""
    layer = _normalize_task_layer(layer)
    payload = generate_backlog(root)
    execution = _lane_execution(payload["execution"], "implementation", layer)
    current_id = execution.get("current_task_id")
    current_phase = execution.get("current_phase")
    config = _get_backlog_config(root)
    tests_enabled = _test_loop_enabled(root)
    execution_options = _execution_config(root)
    if verification_interval is not None:
        config = {**config, "l2_verification_interval": int(verification_interval)}
    if not current_id:
        _enforce_claim_window(execution, execution_options)

    # 1. Se já há uma task em andamento no cursor:
    if current_id:
        if current_id == "task:bootstrap":
            task = _create_injected_bootstrap_task()
            task["checks"] = bootstrap_report(root)
            bootstrap_phase = current_phase if current_phase == "bootstrap" else "implementation"
            bootstrap_kind = "backlog-bootstrap-task" if bootstrap_phase == "bootstrap" else "backlog-task"
            return _task_context(
                root,
                payload,
                task,
                bootstrap_phase,
                bootstrap_kind,
                _bootstrap_instruction(),
            )
        if current_id.startswith("task:verify:"):
            batch_node_ids = execution.get("current_verified_batch_node_ids", [])
            tasks_by_id = {t["id"]: t for t in payload["tasks"]}
            target_nodes = [tasks_by_id[nid] for nid in batch_node_ids if nid in tasks_by_id]
            if not target_nodes:
                for t in payload["tasks"]:
                    if t.get("level") == 2 and (f"task:verify:{t.get('draw_id')}:node:{t.get('node_id')}" == current_id or str(t.get("node_id")) in current_id):
                        target_nodes.append(t)
            if target_nodes:
                task = _create_injected_l2_batch_verify_task(target_nodes)
                return _task_context(
                    root,
                    payload,
                    task,
                    "implementation",
                    "backlog-verification-task",
                    task["verification_instruction"],
                )
        if current_id.startswith("task:associate:"):
            batch_node_ids = execution.get("current_association_node_ids", [])
            tasks_by_id = {t["id"]: t for t in payload["tasks"]}
            target_nodes = [tasks_by_id[nid] for nid in batch_node_ids if nid in tasks_by_id]
            task = _create_injected_l2_association_task(target_nodes) if target_nodes else {"id": current_id, "label": "Associação de símbolos", "status": "in_progress"}
            return _task_context(root, payload, task, "implementation", "backlog-task", "Associe símbolos, arquivos e testes reais no nó correspondente e valide as referências.")
        if current_id == "task:final:verification":
            task = _create_injected_final_task()
            return _task_context(
                root,
                payload,
                task,
                "implementation",
                "backlog-task",
                "Audite a implementação de ponta a ponta do MVP completo em relação à especificação, execute os testes para garantir estabilidade e associe os símbolos e testes aos nós L2 e L3 correspondentes.",
            )

        current = next((task for task in payload["tasks"] if task["id"] == current_id), None)
        if layer is not None and current is not None and not _layer_matches(current, layer):
            current_layer = "frontend" if current.get("level") == 2 else "backend"
            raise ValueError(f"a task atual pertence à camada {current_layer}; conclua-a antes de pedir somente {layer}")
        if tests_enabled and current_phase == "test" and current and not _test_scope_complete(payload, current):
            response = _task_context(root, payload, current, "test", "backlog-test-required")
            response.update({"status": "blocked", "reason": "test_in_progress"})
            return response
        if current_phase == "implementation" and current and current.get("status") == "in_progress":
            return _task_context(root, payload, current, "implementation", "backlog-task")
        if current and current.get("status") == "in_progress":
            return _task_context(root, payload, current, "implementation", "backlog-task")

    # 2. O bootstrap agnóstico é sempre a primeira task operacional, salvo opt-out explícito.
    has_tasks = len(payload["tasks"]) > 0
    bootstrap_enabled = _bootstrap_enabled(config)
    if has_tasks and bootstrap_enabled and not execution.get("bootstrap_done", False):
        task = _create_injected_bootstrap_task()
        task["checks"] = bootstrap_report(root)
        execution["current_task_id"] = task["id"]
        _mark_claim(execution)
        execution["current_backlog_id"] = "system"
        execution["current_phase"] = "implementation"
        write_backlog(root, payload)
        return _task_context(root, payload, task, "implementation", "backlog-task", _bootstrap_instruction())

    # 3. Se o próximo nó L2 ainda não tem testes comprovados, bloqueia avisando backlog-test-required
    pending_task = _next_implementation_task(payload, layer)
    if tests_enabled and pending_task and not _test_scope_complete(payload, pending_task):
        response = _task_context(root, payload, pending_task, "test", "backlog-test-required")
        response.update({"status": "blocked", "reason": "test_missing" if pending_task.get("test_status") == "missing" else "test_not_complete"})
        return response

    # 4. Verifica se há verificação de nó pendente que deve rodar antes das próximas tasks
    interval = config.get("verification_interval", config.get("l2_verification_interval", 0))
    if interval > 0 and layer != "frontend":
        tasks_by_id = {t["id"]: t for t in payload["tasks"]}
        if payload.get("execution", {}).get("development_mode") == "separated":
            l3_tasks = [t for t in payload["tasks"] if t.get("level") == 3]
            verified_ids = set(execution.get("verified_l3_task_ids", execution.get("verified_l2_task_ids", [])))
            completed_l3 = [t for t in l3_tasks if t.get("status") == "done"]
            unverified = [t for t in completed_l3 if t["id"] not in verified_ids]
            all_l3_done = bool(l3_tasks) and all(t.get("status") == "done" for t in l3_tasks)
            if unverified and (len(unverified) >= interval or all_l3_done):
                batch_count = interval if len(unverified) >= interval else len(unverified)
                target_nodes = unverified[:batch_count]
                task = _create_injected_l2_batch_verify_task(target_nodes)
                execution["current_task_id"] = task["id"]
                _mark_claim(execution)
                execution["current_verified_batch_node_ids"] = [n["id"] for n in target_nodes]
                execution["current_backlog_id"] = target_nodes[0].get("backlog_id")
                execution["current_phase"] = "implementation"
                write_backlog(root, payload)
                return _task_context(
                    root,
                    payload,
                    task,
                    "implementation",
                    "backlog-verification-task",
                    task["verification_instruction"],
                )
        else:
            l2_tasks = [t for t in payload["tasks"] if t.get("level") == 2]
            verified_ids = set(execution.get("verified_l2_task_ids", []))
            completed_l2 = [
                t for t in l2_tasks
                if t.get("status") == "done" and all(tasks_by_id.get(cid, {}).get("status") == "done" for cid in t.get("child_task_ids", []))
            ]
            unverified = [t for t in completed_l2 if t["id"] not in verified_ids]
            all_normal_tasks_done = not any(item.get("status") != "done" for item in payload["tasks"])
            if unverified and (len(unverified) >= interval or all_normal_tasks_done):
                batch_count = interval if len(unverified) >= interval else len(unverified)
                target_nodes = unverified[:batch_count]
                task = _create_injected_l2_batch_verify_task(target_nodes)
                execution["current_task_id"] = task["id"]
                _mark_claim(execution)
                execution["current_verified_batch_node_ids"] = [n["id"] for n in target_nodes]
                execution["current_backlog_id"] = target_nodes[0].get("backlog_id")
                execution["current_phase"] = "implementation"
                write_backlog(root, payload)
                return _task_context(
                    root,
                    payload,
                    task,
                    "implementation",
                    "backlog-verification-task",
                    task["verification_instruction"],
                )

    # 5. Busca a próxima task normal do backlog
    task = _next_implementation_task(payload, layer)
    if task is None:
        # Se todas as tasks normais foram concluídas, verifica se precisamos da Task Final
        final_enabled = config.get("final_verification_task", config.get("final_verification_enabled", False))
        if has_tasks and layer is None and final_enabled and not execution.get("final_verification_done", False):
            final_task = _create_injected_final_task()
            execution["current_task_id"] = final_task["id"]
            _mark_claim(execution)
            execution["current_backlog_id"] = "system"
            execution["current_phase"] = "implementation"
            write_backlog(root, payload)
            return _task_context(
                root,
                payload,
                final_task,
                "implementation",
                "backlog-verification-task",
                final_task["verification_instruction"],
            )

        _clear_execution_cursor(execution)
        write_backlog(root, payload)
        if layer is not None:
            return {"kind": "backlog-layer-empty", "status": "complete", "layer": layer, "remaining": 0}
        return {"kind": "backlog-empty", "status": "complete", "remaining": 0}

    task = _implementation_delivery_task(payload, task, layer)

    # 6. Se for nó L2 sem teste comprovado, bloqueia avisando
    if tests_enabled and not _test_scope_complete(payload, task):
        response = _task_context(root, payload, task, "test", "backlog-test-required")
        response.update({"status": "blocked", "reason": "test_missing" if task.get("test_status") == "missing" else "test_not_complete"})
        return response

    # 7. Reserva a task normal de implementação
    task["status"] = "in_progress"
    execution["current_task_id"] = task["id"]
    _mark_claim(execution)
    execution["current_backlog_id"] = task.get("backlog_id")
    execution["current_branch_id"] = task["branch"]["id"]
    execution["branch_position"] = task["branch"]["position"]
    execution["current_phase"] = "implementation"
    execution["current_parent_task_id"] = _parent_task(payload["tasks"], task).get("id")
    execution["current_subtask_id"] = task.get("id") if task.get("parent_task_id") else None
    execution["current_l4_group_task_ids"] = [item["id"] for item in _l4_group_tasks(payload, task)] or None
    for checklist in payload["checklists"]:
        for item in checklist.get("items", []):
            if item.get("id") == task["id"]:
                item["status"] = "in_progress"
    write_backlog(root, payload)
    return _task_context(root, payload, task, "implementation", "backlog-task")


def complete_backlog_task(root: Path, task_id: str) -> dict[str, Any]:
    """Conclui somente a task atualmente reservada para o agente."""
    payload = generate_backlog(root)
    execution = _lane_for_task(payload["execution"], task_id)
    current_id = execution.get("current_task_id")

    if task_id.startswith("change:"):
        if execution.get("current_phase") != "change" or current_id != task_id:
            raise ValueError("a alteração indicada não é a task atual")
        request = next((item for item in _find_change_requests(root) if item["id"] == task_id), None)
        if request is None:
            raise ValueError("pedido de alteração não encontrado ou já concluído")
        document = read_draw(root, request["draw_id"])
        for node in document.get("nodes", []):
            if node.get("id") != request["node_id"]:
                continue
            for change in node.get("changes", []):
                if change.get("id") == request["change_id"]:
                    change["status"] = "done"
                    break
        create_draw(root, document)
        _clear_execution_cursor(execution)
        write_backlog(root, payload)
        response = _change_context({**request, "status": "done"}, "backlog-change-complete", _critical_information(root))
        response["remaining"] = len(_find_change_requests(root))
        return response

    # Tratamento para Bootstrap Task
    if task_id == "task:bootstrap":
        if current_id != "task:bootstrap":
            raise ValueError("task atual não está em andamento")
        config = _get_backlog_config(root)
        checks = bootstrap_report(root)
        if config.get("bootstrap_strict", False) and checks["status"] != "passed":
            raise ValueError("bootstrap bloqueado: " + ", ".join(checks["failures"]))
        bootstrap_phase = execution.get("current_phase") if execution.get("current_phase") in {"bootstrap", "implementation"} else "implementation"
        execution["bootstrap_done"] = True
        _clear_execution_cursor(execution)
        write_backlog(root, payload)
        task = _create_injected_bootstrap_task()
        task["status"] = "done"
        task["checklist_state"] = {"test": True, "implementation": True}
        response = _task_context(root, payload, task, bootstrap_phase, "backlog-bootstrap-complete")
        response.update({"status": "done", "remaining": sum(1 for item in payload["tasks"] if item.get("status") != "done")})
        return response

    # Tratamento para Verificação de Nó L2 (individual ou em lote)
    if task_id.startswith("task:verify:"):
        if current_id != task_id:
            raise ValueError("task atual não está em andamento")
        batch_node_ids = execution.get("current_verified_batch_node_ids", [])
        tasks_by_id = {t["id"]: t for t in payload["tasks"]}
        target_nodes = [tasks_by_id[nid] for nid in batch_node_ids if nid in tasks_by_id]
        if not target_nodes:
            for t in payload["tasks"]:
                if t.get("level") == 2 and (f"task:verify:{t.get('draw_id')}:node:{t.get('node_id')}" == task_id or str(t.get("node_id")) in task_id):
                    target_nodes.append(t)

        verified_l2 = execution.setdefault("verified_l2_task_ids", [])
        verified_l3 = execution.setdefault("verified_l3_task_ids", [])
        for n in target_nodes:
            if n.get("level") == 3:
                if n["id"] not in verified_l3:
                    verified_l3.append(n["id"])
            elif n["id"] not in verified_l2:
                verified_l2.append(n["id"])

        execution.pop("current_verified_batch_node_ids", None)
        if _get_backlog_config(root).get("l2_post_verification_tasks", False):
            association = _create_injected_l2_association_task(target_nodes)
            execution["current_task_id"] = association["id"]
            execution["current_association_node_ids"] = [node["id"] for node in target_nodes]
            execution["current_phase"] = "implementation"
            _mark_claim(execution)
            write_backlog(root, payload)
            response = _task_context(root, payload, association, "implementation", "backlog-task", "Associe símbolos, arquivos e testes reais no nó correspondente e valide as referências.")
            response.update({"status": "in_progress"})
            return response
        _clear_execution_cursor(execution)
        write_backlog(root, payload)
        task = _create_injected_l2_batch_verify_task(target_nodes) if target_nodes else {
            "id": task_id, "label": "Verificação Funcional", "level": 2, "status": "done"
        }
        task["status"] = "done"
        task["checklist_state"] = {"test": True, "implementation": True}
        response = _task_context(root, payload, task, "implementation", "backlog-complete")
        response.update({"status": "done", "remaining": sum(1 for item in payload["tasks"] if item.get("status") != "done")})
        return response

    if task_id.startswith("task:associate:"):
        if current_id != task_id:
            raise ValueError("task atual não está em andamento")
        execution.pop("current_association_node_ids", None)
        _clear_execution_cursor(execution)
        write_backlog(root, payload)
        task = {"id": task_id, "label": "Associação de símbolos, arquivos e testes", "status": "done", "level": 2}
        response = _task_context(root, payload, task, "implementation", "backlog-complete")
        response.update({"status": "done", "remaining": sum(1 for item in payload["tasks"] if item.get("status") != "done")})
        return response

    # Tratamento para Task Final
    if task_id == "task:final:verification":
        if current_id != "task:final:verification":
            raise ValueError("task atual não está em andamento")
        execution["final_verification_done"] = True
        _clear_execution_cursor(execution)
        write_backlog(root, payload)
        task = _create_injected_final_task()
        task["status"] = "done"
        task["checklist_state"] = {"test": True, "implementation": True}
        response = _task_context(root, payload, task, "implementation", "backlog-complete")
        response.update({"status": "done", "remaining": 0})
        return response

    current = next((item for item in payload["tasks"] if item["id"] == current_id), None)
    requested = next((item for item in payload["tasks"] if item["id"] == task_id), None)
    if requested is None:
        raise ValueError("task-id não existe no backlog")
    if current_id != task_id:
        if current is None or requested.get("id") not in current.get("child_task_ids", []):
            raise ValueError("task-id não corresponde à task atual ou a uma subtask do contexto atual")
        if execution.get("current_phase") == "test":
            requested.setdefault("checklist_state", _default_checklist_state(requested))["test"] = True
        else:
            if _test_loop_enabled(root) and not _test_scope_complete(payload, current):
                raise ValueError("teste do nó e dos subfluxos ainda não foi concluído")
            requested["status"] = "done"
            requested.setdefault("checklist_state", _default_checklist_state(requested))["implementation"] = True
        _refresh_task_checklist_items(payload)
        write_backlog(root, payload)
        response = _task_context(root, payload, current, execution.get("current_phase") or "implementation", "backlog-subtask-complete")
        response.update({"status": "test-done" if execution.get("current_phase") == "test" else "done", "completed_task_id": task_id})
        return response
    task = next((item for item in payload["tasks"] if item["id"] == task_id), None)
    if task is None:
        raise ValueError("task atual não está em andamento")
    if execution.get("current_phase") == "test":
        previous_status = task.pop("test_previous_status", None)
        task["test_status"] = "done"
        task.pop("test_manual", None)
        if _task_delivery_scope(payload) == "task":
            task["test_completed_independently"] = True
        if task.get("level") in {3, 4} and _l3_parent_task(payload, task) is not None:
            scope_tasks = _test_scope_tasks(payload, task)
        else:
            scope_tasks = [task] if _task_delivery_scope(payload) == "task" else _test_scope_tasks(payload, task)
        if task.get("level") == 2 and _phase_loop_options(payload, "test").get("l2_children_mode") == "owned":
            scope_tasks = _test_scope_tasks(payload, task)
        for scope_task in scope_tasks:
            scope_task["test_status"] = "done"
            scope_task["test_completed_independently"] = True
            scope_task.setdefault("checklist_state", _default_checklist_state(scope_task))["test"] = True
        if previous_status == "pending":
            task["status"] = "pending"
        _clear_execution_cursor(execution)
        _refresh_task_checklist_items(payload)
        write_backlog(root, payload)
        response = _task_context(root, payload, task, "test", "backlog-test-complete")
        response.update({"status": "test-done", "remaining": len(_pending_test_tasks(payload))})
        return response
    if task.get("status") != "in_progress":
        raise ValueError("task atual não está em andamento")
    if _test_loop_enabled(root) and not _test_scope_complete(payload, task):
        raise ValueError("teste da task ainda não foi comprovado")
    if task.get("level") in {3, 4} and _l3_parent_task(payload, task) is not None:
        scope_tasks = _l4_delivery_tasks(payload, task)
        for scope_task in scope_tasks:
            if scope_task.get("level") == 4:
                scope_task["status"] = "done"
            scope_task.setdefault("checklist_state", _default_checklist_state(scope_task))["implementation"] = True
        l3_parent = _l3_parent_task(payload, task)
        remaining_l4 = _l4_group_tasks(payload, l3_parent or task)
        if l3_parent is not None:
            l3_parent["status"] = "pending" if remaining_l4 else "done"
            l3_parent.setdefault("checklist_state", _default_checklist_state(l3_parent))["implementation"] = not remaining_l4
        _clear_execution_cursor(execution)
        _refresh_branch_completion(payload)
        _refresh_task_checklist_items(payload)
        write_backlog(root, payload)
        response = _task_context(root, payload, task, "implementation", "backlog-complete")
        response.update({
            "status": "done",
            "completed_task_ids": [scope_task.get("id") for scope_task in scope_tasks],
            "l4_group_task_ids": [scope_task.get("id") for scope_task in scope_tasks if scope_task.get("level") == 4],
            "remaining": sum(1 for item in payload["tasks"] if item.get("status") != "done"),
        })
        return response
    if _phase_loop_options(payload, "implementation").get("l2_children_mode") == "owned" and task.get("level") == 2:
        scope_tasks = _test_scope_tasks(payload, task)
        for scope_task in scope_tasks:
            scope_task["status"] = "done"
            scope_task.setdefault("checklist_state", _default_checklist_state(scope_task))["implementation"] = True
        _clear_execution_cursor(execution)
        _refresh_branch_completion(payload)
        _refresh_task_checklist_items(payload)
        write_backlog(root, payload)
        response = _task_context(root, payload, task, "implementation", "backlog-complete")
        response.update({
            "status": "done",
            "completed_task_ids": [scope_task.get("id") for scope_task in scope_tasks],
            "owned_child_task_ids": [scope_task.get("id") for scope_task in scope_tasks[1:]],
            "remaining": sum(1 for item in payload["tasks"] if item.get("status") != "done"),
        })
        return response
    if _task_delivery_scope(payload) == "node" and _phase_loop_options(payload, "implementation").get("l2_children_mode") != "context":
        scope_tasks = _test_scope_tasks(payload, task)
        for scope_task in scope_tasks:
            scope_task["status"] = "done"
            scope_task.setdefault("checklist_state", _default_checklist_state(scope_task))["implementation"] = True
        _clear_execution_cursor(execution)
        _refresh_branch_completion(payload)
        _refresh_task_checklist_items(payload)
        write_backlog(root, payload)
        response = _task_context(root, payload, task, "implementation", "backlog-complete")
        response.update({
            "status": "done",
            "completed_task_ids": [scope_task.get("id") for scope_task in scope_tasks],
            "remaining": sum(1 for item in payload["tasks"] if item.get("status") != "done"),
        })
        return response
    task["status"] = "done"
    task.setdefault("checklist_state", _default_checklist_state(task))["implementation"] = True
    for checklist in payload["checklists"]:
        for item in checklist.get("items", []):
            if item.get("id") == task_id:
                item["status"] = "done"
    _clear_execution_cursor(execution)
    _refresh_branch_completion(payload)
    _refresh_task_checklist_items(payload)
    write_backlog(root, payload)
    response = _task_context(root, payload, task, "implementation", "backlog-complete")
    response.update({"status": "done", "remaining": sum(1 for item in payload["tasks"] if item.get("status") != "done")})
    return response
