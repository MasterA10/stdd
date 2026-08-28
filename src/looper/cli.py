import errno
import json
import os
import signal
import subprocess
import sys
from typing import Iterable, List, Optional
from pathlib import Path

import typer

from .core import (
    ensure_gitignore,
    get_incremental_draw_diff,
    get_logged_draw_diff,
    init_project,
    project_root,
    record_run_entry,
    run_tests,
)
from .backlog import (
    complete_backlog_task,
    generate_backlog,
    get_backlog_config,
    missing_backlog,
    next_backlog_task,
    next_backlog_test,
    next_backlog_change,
    set_backlog_config,
    VALID_TASK_DELIVERY_SCOPES,
    VALID_DEVELOPMENT_MODES,
    VALID_LOOP_MODES,
    VALID_CHILDREN_MODES,
)
from .draw import (
    analyze_draw_contract,
    analyze_draw_structure,
    collect_draw_symbols,
    consume_observation,
    create_draw,
    find_addressed_questions,
    format_draw_answers,
    logical_draw_payload,
    read_draw_index,
    add_draw_change,
    serve_draw,
)
from .reviews import maybe_review_completed_task, run_review, set_review_enabled
from .config import config_path, instructions
from .improvements import create_improvement, list_ready_improvements, mark_improvement_applied
from .traceability import associate_node_reference, associate_node_references
from .setup import (
    SUPPORTED_INTEGRATIONS,
    available_integrations,
    configure_project,
    ensure_stack_gitignore,
)

app = typer.Typer(help="Looper: CLI de suporte ao desenvolvimento orientado por testes.")
config_app = typer.Typer(help="Configurações interativas do Looper.")
app.add_typer(config_app, name="config")
draw_app = typer.Typer(help="Cria e visualiza desenhos JSON do projeto.")
app.add_typer(draw_app, name="draw")
draw_change_app = typer.Typer(help="Gerencia changes pendentes dos nós.")
draw_app.add_typer(draw_change_app, name="change")
backlog_app = typer.Typer(help="Gera e executa tasks derivadas dos Draws.")
app.add_typer(backlog_app, name="backlog")


def _human_answer(value: object) -> str:
    """Converte uma resposta do Draw em uma linha curta e legível."""
    if isinstance(value, bool):
        return "sim" if value else "não"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(", ", ": "))
    return str(value).strip()


def _first_answer(questions: object) -> tuple[str, str] | None:
    """Retorna somente a primeira decisão respondida, sem expor alternativas."""
    if not isinstance(questions, list):
        return None
    for question in questions:
        if not isinstance(question, dict) or "answer" not in question or question.get("answer") is None:
            continue
        prompt = str(question.get("prompt") or "Decisão registrada").strip()
        answer = _human_answer(question["answer"])
        if answer:
            return prompt, answer
    return None


def _compact_backlog_response(response: dict[str, object]) -> dict[str, object]:
    """Seleciona o contexto mínimo necessário para uma task do backlog."""
    task = response.get("task") if isinstance(response.get("task"), dict) else {}
    parent = response.get("parent_task") if isinstance(response.get("parent_task"), dict) else {}
    compact: dict[str, object] = {
        "kind": response.get("kind"),
        "phase": response.get("phase"),
        "status": response.get("status") or task.get("status"),
        "task_id": task.get("id"),
        "task": task.get("label"),
        "draw": task.get("draw_title") or task.get("draw_id"),
        "node_id": task.get("node_id"),
        "description": task.get("description"),
        "success_criteria": response.get("success_criteria") or task.get("success_criteria") or None,
        "failure_criteria": response.get("failure_criteria") or task.get("failure_criteria") or None,
        "symbols": task.get("symbols") or [],
        "verification_requirements": task.get("verification_requirements") or [],
        "navigation_target": response.get("navigation_target"),
        "navigation_entries": response.get("navigation_entries") or [],
        "previous_node": response.get("previous_node"),
        "connection": response.get("connection"),
        "condition": response.get("condition"),
        "path": response.get("path"),
        "state": response.get("state"),
        "task_delivery_scope": response.get("task_delivery_scope"),
        "development_mode": response.get("development_mode"),
        "implementation_layer": response.get("implementation_layer"),
        "tests_required": response.get("tests_required"),
        "is_first_l3_for_screen": response.get("is_first_l3_for_screen"),
        "parent_screen_context": response.get("parent_screen_context"),
        "batch": response.get("batch"),
        "batch_size": response.get("batch_size"),
        "l4_group_size": response.get("l4_group_size"),
        "l4_group": response.get("l4_group"),
        "l4_parent": response.get("l4_parent"),
        "l4_delivery_note": response.get("l4_delivery_note"),
        "children_delivery_mode": response.get("children_delivery_mode"),
        "children_context": response.get("children_context"),
        "context_parent": response.get("context_parent"),
        "owned_child_task_ids": response.get("owned_child_task_ids"),
        "l3_loop_enabled": response.get("l3_loop_enabled"),
        "critical_information": response.get("critical_information"),
        "instruction": response.get("instruction"),
    }
    if parent.get("id") and parent.get("id") != task.get("id"):
        compact["parent"] = parent.get("label")
    decision = _first_answer(task.get("questions"))
    if decision is not None:
        compact["decision"] = {"question": decision[0], "answer": decision[1]}
    if task.get("verified_nodes"):
        compact["verified_nodes"] = task.get("verified_nodes")
    if isinstance(response.get("level_context"), dict):
        compact["level_context"] = response["level_context"]
    if response.get("task_delivery_scope") == "node" and isinstance(response.get("delivery_subtasks"), list):
        compact["delivery_subtasks"] = response["delivery_subtasks"]
    compact["delivery_scope_note"] = response.get("delivery_scope_note")
    reason_labels = {
        "test_missing": "os testes da task ainda não foram comprovados",
        "test_not_complete": "o checklist de testes ainda não foi concluído",
        "test_in_progress": "a task está aguardando a conclusão dos testes",
    }
    if response.get("reason") is not None:
        compact["reason"] = reason_labels.get(str(response["reason"]), response["reason"])
    for key in ("instruction", "remaining", "completed_task_id", "access_paths"):
        if response.get(key) is not None:
            compact[key] = response[key]
    return {key: value for key, value in compact.items() if value not in (None, "", [])}


def _format_level_context(level_context: object) -> list[str]:
    """Renderiza a diretriz semântica de L2/L3 para a saída humana."""
    if not isinstance(level_context, dict):
        return []
    lines = [f"Escopo do nível {level_context.get('level')}: {level_context.get('meaning')}"]
    guidance = level_context.get("guidance")
    if guidance:
        lines.append(f"Diretriz: {guidance}")
    return lines


def _format_navigation_context(compact: dict[str, object]) -> list[str]:
    """Renderiza destino e entradas da navegação em linguagem acionável."""
    target = compact.get("navigation_target")
    if not isinstance(target, dict):
        return []
    target_kind = target.get("kind")
    lines: list[str] = []
    if target_kind == "screen":
        lines.append(f"Tela de destino: {target.get('label', target.get('node_id'))}")
    else:
        screen_label = target.get("screen_label")
        if screen_label:
            lines.append(f"Tela relacionada: {screen_label}")
        lines.append(f"Etapa interna: {target.get('label', target.get('node_id'))}")

    entries = compact.get("navigation_entries")
    if not isinstance(entries, list) or not entries:
        if target_kind == "screen":
            lines.append("Entrada: início do fluxo; nenhuma tela de origem foi registrada.")
        return lines

    lines.append(f"Entradas possíveis ({len(entries)}):")
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            continue
        origin = entry.get("origin") if isinstance(entry.get("origin"), dict) else {}
        destination = entry.get("target") if isinstance(entry.get("target"), dict) else target
        origin_label = origin.get("label", origin.get("node_id", "origem"))
        destination_label = destination.get("label", destination.get("node_id", "destino"))
        origin_kind = "Tela de origem" if target_kind == "screen" else "Etapa anterior"
        lines.append(f"  {index}. {origin_kind}: {origin_label}")
        if origin.get("description"):
            lines.append(f"     Descrição: {origin['description']}")
        if entry.get("condition_label"):
            lines.append(f"     Condição: {entry['condition_label']}")
        if entry.get("action"):
            lines.append(f"     Ação: {entry['action']}")
        elif entry.get("label"):
            lines.append(f"     Entrada: {entry['label']}")
        lines.append(f"     Transição: {origin_label} → {destination_label}")
    return lines


def _format_backlog_response(response: dict[str, object]) -> str:
    """Renderiza uma task sem o ruído do payload completo do backlog."""
    kind = response.get("kind")
    compact_preview = response.get("critical_information")
    critical = compact_preview if compact_preview is not None else response.get("critical_information")
    if isinstance(critical, dict):
        critical_content = str(critical.get("content") or "").strip()
    else:
        try:
            from .config import load_config
            critical_content = instructions(load_config(project_root())).strip()
        except (OSError, UnicodeError):
            critical_content = ""

    def with_critical(text: str) -> str:
        return (
            f"INFORMAÇÃO CRÍTICA DO PROJETO:\n{critical_content}\nFIM DA INFORMAÇÃO CRÍTICA.\n\n{text}"
            if critical_content else text
        )

    if kind == "backlog-empty":
        return with_critical("Backlog concluído. Não há tasks pendentes.")
    if kind == "backlog-change-empty":
        return with_critical("Loop de alterações concluído. Não há pedidos pendentes.")
    if kind == "backlog-test-empty":
        return with_critical("Fase de testes concluída. Não há tasks de teste pendentes.")
    if kind == "backlog-test-disabled":
        return with_critical("Loop de testes desabilitado. O backlog entrega somente implementação; use looper backlog task.")
    if kind == "backlog-layer-empty":
        return with_critical(f"Não há tasks pendentes para a camada {response.get('layer', 'solicitada')}. O restante do backlog continua disponível.")

    compact = _compact_backlog_response(response)
    if kind == "backlog-bootstrap-task":
        title = "Preparação inicial"
    elif kind == "backlog-test-required":
        title = "Teste necessário antes da implementação"
    elif kind == "backlog-test-task":
        title = "Task de teste"
    elif kind == "backlog-verification-task":
        title = "Verificação obrigatória da implementação"
    elif kind == "backlog-change-task":
        title = "Task de alteração"
    else:
        title = "Task de implementação"

    lines = [title]
    if critical_content:
        lines.extend(["INFORMAÇÃO CRÍTICA DO PROJETO:", critical_content, "FIM DA INFORMAÇÃO CRÍTICA."])
    if compact.get("task"):
        lines.append(f"Task: {compact['task']}")
    if compact.get("draw"):
        lines.append(f"Fluxo: {compact['draw']}")
    if compact.get("parent"):
        lines.append(f"Contexto: {compact['parent']}")
    if compact.get("node_id") is not None:
        lines.append(f"Nó: {compact['node_id']}")
    if compact.get("task_id"):
        lines.append(f"ID: {compact['task_id']}")
    if compact.get("development_mode"):
        lines.append(f"Arquitetura do loop: {compact['development_mode']}")
    if compact.get("implementation_layer"):
        lines.append(f"Camada: {compact['implementation_layer']}")
    if compact.get("tests_required") is False:
        lines.append("Testes: não aplicáveis nesta fase de frontend")
    if compact.get("description"):
        lines.append(f"Descrição: {compact['description']}")
    if compact.get("success_criteria"):
        lines.append(f"Critério de sucesso: {compact['success_criteria']}")
    if compact.get("failure_criteria"):
        lines.append(f"Critério de falha: {compact['failure_criteria']}")
    delivery_subtasks = compact.get("delivery_subtasks")
    if isinstance(delivery_subtasks, list):
        scope_action = "criar testes para" if kind in {"backlog-test-task", "backlog-test-required"} else "implementar"
        lines.append(f"Escopo obrigatório: {scope_action} o nó inteiro e todos os subfluxos internos")
        lines.append(f"Escopo entregue: nó e {len(delivery_subtasks)} subfluxo(s) interno(s)")
        for subtask in delivery_subtasks:
            if isinstance(subtask, dict):
                lines.append(f"  • {subtask.get('label', 'Subfluxo')} (ID: {subtask.get('id')})")
        note = compact.get("delivery_scope_note")
        if note:
            lines.append(f"Regra do escopo: {note}")
    parent_screen = compact.get("parent_screen_context")
    if isinstance(parent_screen, dict):
        lines.append("Tela pai correspondente (L2):")
        lines.append(f"  • Tela: {parent_screen.get('label', parent_screen.get('node_id'))} (Nó {parent_screen.get('node_id')})")
        if parent_screen.get("description"):
            lines.append(f"    Descrição: {parent_screen.get('description')}")
        screen_syms = parent_screen.get("symbols")
        if isinstance(screen_syms, list) and screen_syms:
            lines.append(f"    Símbolos da tela: {', '.join(screen_syms)}")
    batch_items = compact.get("batch")
    if isinstance(batch_items, list) and len(batch_items) > 1:
        lines.append(f"Nós no lote ({len(batch_items)}):")
        for b_item in batch_items:
            lines.append(f"  • {b_item.get('label', b_item.get('id'))} (ID: {b_item.get('id')})")
    l4_parent = compact.get("l4_parent")
    l4_group = compact.get("l4_group")
    if isinstance(l4_parent, dict):
        lines.append(f"Pai L3: {l4_parent.get('label', l4_parent.get('id'))} (ID: {l4_parent.get('id')})")
    if isinstance(l4_group, list):
        lines.append(f"Nós L4 no grupo ({len(l4_group)}):")
        for l4_item in l4_group:
            if isinstance(l4_item, dict):
                lines.append(f"  • {l4_item.get('label', l4_item.get('id'))} (ID: {l4_item.get('id')})")
    if compact.get("l4_delivery_note"):
        lines.append(f"Regra L4: {compact['l4_delivery_note']}")
    if compact.get("children_delivery_mode"):
        lines.append(f"Filhos L3: {compact['children_delivery_mode']}")
    if isinstance(compact.get("children_context"), list):
        lines.append(f"Contexto L3 associado: {len(compact['children_context'])} nó(s)")
    if compact.get("context_parent"):
        lines.append("Contexto L2 pai: incluído")
    if compact.get("l3_loop_enabled") is False:
        lines.append("Loop L3: desabilitado nesta fase")
    lines.extend(_format_level_context(compact.get("level_context")))
    lines.extend(_format_navigation_context(compact))
    verified_nodes = compact.get("verified_nodes")
    if kind == "backlog-verification-task" and isinstance(verified_nodes, list) and verified_nodes:
        lines.append("Alvos da verificação:")
        for vn in verified_nodes:
            lbl = vn.get("label", f"Nó {vn.get('node_id')}")
            syms = ", ".join(vn.get("symbols", []))
            syms_str = f" [Símbolos: {syms}]" if syms else ""
            lines.append(f"  • Nó {vn.get('node_id')}: {lbl}{syms_str}")
            references = vn.get("code_refs")
            if isinstance(references, list) and references:
                lines.append("    Arquivos e símbolos para ler:")
                for reference in references:
                    if isinstance(reference, str):
                        lines.append(f"      - {reference}")
                        continue
                    if not isinstance(reference, dict):
                        continue
                    symbol = reference.get("symbol") or reference.get("qualified_name")
                    file = reference.get("file")
                    if file and symbol:
                        lines.append(f"      - {file} — {symbol}")
                    elif file or symbol:
                        lines.append(f"      - {file or symbol}")
    elif isinstance(verified_nodes, list) and len(verified_nodes) > 1:
        lines.append(f"Nós no lote ({len(verified_nodes)}):")
        for vn in verified_nodes:
            lbl = vn.get("label", f"Nó {vn.get('node_id')}")
            syms = ", ".join(vn.get("symbols", []))
            syms_str = f" [Símbolos: {syms}]" if syms else ""
            lines.append(f"  • Nó {vn.get('node_id')}: {lbl}{syms_str}")
    requirements = compact.get("verification_requirements")
    if kind == "backlog-verification-task" and isinstance(requirements, list) and requirements:
        lines.append("Procedimento obrigatório:")
        for index, requirement in enumerate(requirements, start=1):
            lines.append(f"  {index}. {requirement}")
    decision = compact.get("decision")
    if isinstance(decision, dict):
        lines.append(f"Decisão: {decision['question']} → {decision['answer']}")
    symbols = compact.get("symbols")
    lines.append("Símbolos: " + (", ".join(str(symbol) for symbol in symbols) if isinstance(symbols, list) and symbols else "nenhum associado"))
    if compact.get("reason"):
        lines.append(f"Bloqueio: {compact['reason']}")
    if compact.get("instruction"):
        instruction_label = "Instrução da auditoria" if kind == "backlog-verification-task" else "Próximo passo"
        lines.append(f"{instruction_label}: {compact['instruction']}")
    access_paths = compact.get("access_paths")
    if isinstance(access_paths, list):
        for path in access_paths:
            lines.append(f"Origem: {path.replace(' → Nó atual', '')}")
    return "\n".join(lines)


@app.command()
def init(
    project: Path = typer.Argument(Path("."), help="Diretório do projeto a inicializar; por padrão, o diretório atual."),
    integration: List[str] = typer.Option(None, "--integration", help="Agente a integrar: codex, claude ou gemini; pode repetir."),
    all_integrations: bool = typer.Option(False, "--all-integrations", help="Instala as skills para Codex, Claude e Gemini."),
    interactive: bool = typer.Option(False, "--interactive", help="Abre a seleção numérica de integrações e setup."),
    task_delivery_scope: Optional[str] = typer.Option(None, "--task-delivery-scope", help="Como entregar as tasks em testes e implementação: node (tela, funcionamento e internos juntos) ou task (uma por vez)."),
    development_mode: Optional[str] = typer.Option(None, "--development-mode", help="Ordem arquitetural: sequential ou separated (todas as telas L2 antes do backend L3)."),
    l2_verification_interval: Optional[int] = typer.Option(None, "--l2-verification-interval", "--verification-interval", min=0, help="Insere uma task de conferência a cada N nós concluídos; 0 desabilita."),
    test_loop_enabled: Optional[bool] = typer.Option(None, "--test-loop/--no-test-loop", help="Habilita ou desabilita a fase de testes do backlog; desabilitada entrega somente implementação."),
    task_batch_size: Optional[int] = typer.Option(None, "--task-batch-size", min=1, max=5, help="Quantidade de tasks entregues no lote para o backend (1 a 5)."),
    l4_group_size: Optional[int] = typer.Option(None, "--l4-group-size", min=1, max=50, help="Quantidade de nós L4 entregues junto com cada pai L3 (1 a 50)."),
    task_batch_scope: Optional[str] = typer.Option(None, "--task-batch-scope", help="Escopo do lote: task ou node."),
    bootstrap: Optional[bool] = typer.Option(None, "--bootstrap/--no-bootstrap", help="Habilita ou desabilita a task de bootstrap inicial."),
    final_verification: Optional[bool] = typer.Option(None, "--final-verification/--no-final-verification", help="Habilita ou desabilita a task de verificação final E2E."),
    min_task_interval_seconds: Optional[int] = typer.Option(None, "--min-task-interval-seconds", min=0, help="Janela mínima anti-script entre avanços."),
    test_loop_mode: Optional[str] = typer.Option(None, "--test-loop-mode", help="Preset do loop de testes."),
    implementation_loop_mode: Optional[str] = typer.Option(None, "--implementation-loop-mode", help="Preset do loop de implementação."),
    test_batch_size: Optional[int] = typer.Option(None, "--test-batch-size", min=1, help="Quantidade de unidades por avanço no loop de testes."),
    implementation_batch_size: Optional[int] = typer.Option(None, "--implementation-batch-size", min=1, help="Quantidade de unidades por avanço no loop de implementação."),
    l2_children_mode: Optional[str] = typer.Option(None, "--l2-children-mode", help="Filhos L3 no L2: none, context ou owned."),
    l3_loop_enabled: Optional[bool] = typer.Option(None, "--l3-loop/--no-l3-loop", help="Habilita ou desabilita o loop L3."),
    l3_include_parent: Optional[bool] = typer.Option(None, "--l3-parent-context/--no-l3-parent-context", help="Inclui o L2 pai no contexto do L3."),
    review_enabled: Optional[bool] = typer.Option(None, "--review/--no-review", help="Habilita ou desabilita a revisão automática por subagente."),
    web: Optional[bool] = typer.Option(None, "--web/--no-web", help="Abre a interface web de configuração após inicializar."),
    port: int = typer.Option(8765, "--port", min=1, max=65535, help="Porta local da interface web."),
) -> None:
    """Inicializa a estrutura do Looper e instala as skills dos agentes.
    Cria o diretório-alvo quando necessário, depois cria .looper/ e .agents/skills.
    """
    target = project.expanduser().resolve()
    if target.exists() and not target.is_dir():
        typer.echo(f"Erro: o destino não é um diretório: {target}", err=True)
        raise typer.Exit(1)
    target.mkdir(parents=True, exist_ok=True)
    requested = tuple(integration or ("codex",))
    if all_integrations:
        requested = SUPPORTED_INTEGRATIONS
    # A configuração deixou de ser um wizard de terminal. O init usa o Codex
    # como padrão e abre o editor web quando executado em um terminal real.
    invalid = sorted(set(requested) - set(SUPPORTED_INTEGRATIONS))
    if invalid:
        typer.echo(f"Erro: integrações desconhecidas: {', '.join(invalid)}", err=True)
        raise typer.Exit(1)
    if task_delivery_scope is not None and task_delivery_scope not in VALID_TASK_DELIVERY_SCOPES:
        typer.echo("Erro: --task-delivery-scope deve ser node ou task.", err=True)
        raise typer.Exit(1)
    if development_mode is not None and development_mode not in VALID_DEVELOPMENT_MODES:
        typer.echo("Erro: --development-mode deve ser sequential ou separated.", err=True)
        raise typer.Exit(1)
    if test_loop_mode is not None and test_loop_mode not in VALID_LOOP_MODES:
        typer.echo("Erro: --test-loop-mode inválido.", err=True)
        raise typer.Exit(1)
    if implementation_loop_mode is not None and implementation_loop_mode not in VALID_LOOP_MODES:
        typer.echo("Erro: --implementation-loop-mode inválido.", err=True)
        raise typer.Exit(1)
    if l2_children_mode is not None and l2_children_mode not in VALID_CHILDREN_MODES:
        typer.echo("Erro: --l2-children-mode deve ser none, context ou owned.", err=True)
        raise typer.Exit(1)
    created = init_project(target, integrations=requested, development_mode=development_mode)
    if review_enabled is not None:
        set_review_enabled(target, review_enabled)
    typer.echo(f"Projeto inicializado em {target}. {len(created)} itens criados ou atualizados.")
    if task_delivery_scope is not None or l2_verification_interval is not None or test_loop_enabled is not None or development_mode is not None or task_batch_size is not None or l4_group_size is not None or task_batch_scope is not None or bootstrap is not None or final_verification is not None or min_task_interval_seconds is not None or test_loop_mode is not None or implementation_loop_mode is not None or test_batch_size is not None or implementation_batch_size is not None or l2_children_mode is not None or l3_loop_enabled is not None or l3_include_parent is not None:
        set_backlog_config(
            target,
            task_delivery_scope=task_delivery_scope,
            verification_interval=l2_verification_interval,
            test_loop_enabled=test_loop_enabled,
            development_mode=development_mode,
            task_batch_size=task_batch_size,
            l4_group_size=l4_group_size,
            task_batch_scope=task_batch_scope,
            bootstrap_task=bootstrap,
            final_verification_task=final_verification,
            min_task_interval_seconds=min_task_interval_seconds,
            test_loop_mode=test_loop_mode,
            implementation_loop_mode=implementation_loop_mode,
            test_batch_size=test_batch_size,
            implementation_batch_size=implementation_batch_size,
            l2_children_mode=l2_children_mode,
            l3_loop_enabled=l3_loop_enabled,
            l3_include_parent=l3_include_parent,
        )
    should_open_web = web if web is not None else sys.stdin.isatty()
    if should_open_web:
        typer.echo("Abrindo a configuração web do Looper…")
        try:
            serve_draw(target, port=port, initial_path="/.looper/draw.html?settings=1", open_browser=True)
        except (RuntimeError, ValueError, OSError) as error:
            typer.echo(f"Erro ao abrir a interface web: {error}", err=True)
            raise typer.Exit(1)
    unavailable = [name for name, found in available_integrations().items() if name in requested and not found]
    if unavailable:
        typer.echo(f"Aviso: agente(s) não encontrado(s) no PATH: {', '.join(unavailable)}.", err=True)


def choose_integrations() -> tuple[str, ...]:
    """Apresenta uma seleção múltipla numerada para os agentes disponíveis.
    Aceita números separados por vírgula ou a opção todos e retorna integrações únicas.
    """
    typer.echo("Selecione as integrações do agente (ex.: 1,3 ou 4 para todos):")
    for index, name in enumerate((*SUPPORTED_INTEGRATIONS, "todos"), start=1):
        typer.echo(f"  {index}. {name.title()}")
    answer = typer.prompt("Integrações", default="1")
    choices = {part.strip() for part in answer.split(",") if part.strip()}
    if "4" in choices or "todos" in {choice.lower() for choice in choices}:
        return SUPPORTED_INTEGRATIONS
    selected = tuple(
        name for index, name in enumerate(SUPPORTED_INTEGRATIONS, start=1) if str(index) in choices
    )
    if not selected:
        typer.echo("Nenhuma opção válida; usando Codex.")
        return ("codex",)
    return selected


def choose_level_meanings() -> tuple[str, str]:
    """Define o significado operacional dos níveis 2 e 3 no backlog."""
    typer.echo("Defina o que cada nível do Draw significa para as tasks do backlog:")
    typer.echo("Nível 2:")
    typer.echo("  1. Tela — implementação da view/tela e do frontend")
    typer.echo("  2. Outro — digitar uma definição personalizada")
    level_2_choice = typer.prompt("Significado do nível 2", default="1").strip()
    if level_2_choice == "1":
        level_2_meaning = "Tela"
    elif level_2_choice == "2":
        level_2_meaning = typer.prompt("Digite o significado do nível 2").strip()
    else:
        level_2_meaning = level_2_choice

    typer.echo("Nível 3:")
    typer.echo("  1. Regra de negócio")
    typer.echo("  2. Detalhes da tela")
    typer.echo("  3. Outro — digitar uma definição personalizada")
    level_3_choice = typer.prompt("Significado do nível 3", default="1").strip()
    if level_3_choice == "1":
        level_3_meaning = "Regra de negócio"
    elif level_3_choice == "2":
        level_3_meaning = "Detalhes da tela"
    elif level_3_choice == "3":
        level_3_meaning = typer.prompt("Digite o significado do nível 3").strip()
    else:
        level_3_meaning = level_3_choice

    if not level_2_meaning or not level_3_meaning:
        raise typer.BadParameter("Os significados dos níveis não podem ficar vazios.")
    return level_2_meaning, level_3_meaning


def choose_task_delivery_scope() -> str:
    """Define se o backlog entrega o nó com internos ou cada task separada."""
    typer.echo("Defina como o backlog deve entregar as tasks:")
    typer.echo("  1. Nó de nível 2, tela, funcionamento e subfluxos internos juntos")
    typer.echo("  2. Separar o nó de nível 2 e cada subfluxo interno")
    choice = typer.prompt("Escopo das tasks", default="2").strip()
    if choice == "1":
        return "node"
    if choice == "2":
        return "task"
    if choice in VALID_TASK_DELIVERY_SCOPES:
        return choice
    raise typer.BadParameter("Escolha 1, 2, node ou task.")


def choose_l2_verification_interval() -> int:
    """Define a frequência das tasks que conferem a implementação dos nós L2."""
    typer.echo("Defina quando conferir a implementação dos nós L2:")
    typer.echo("  0. Não inserir conferência automática")
    typer.echo("  1. Após cada nó L2 concluído")
    typer.echo("  N. Após cada N nós L2 concluídos, em lote")
    answer = typer.prompt("Intervalo de conferência", default="1").strip()
    try:
        interval = int(answer)
    except ValueError as error:
        raise typer.BadParameter("Digite um número inteiro maior ou igual a zero.") from error
    if interval < 0:
        raise typer.BadParameter("O intervalo de conferência não pode ser negativo.")
    return interval


def choose_test_loop_enabled() -> bool:
    """Define se o backlog executará a fase de testes."""
    typer.echo("Defina se o backlog deve gerar tasks de teste:")
    typer.echo("  1. Sim — executar testes antes da implementação")
    typer.echo("  2. Não — entregar somente o loop de implementação")
    choice = typer.prompt("Loop de testes", default="1").strip()
    if choice == "1":
        return True
    if choice == "2":
        return False
    raise typer.BadParameter("Escolha 1 ou 2.")


@app.command()
def setup(
    project: Path = typer.Argument(Path("."), help="Diretório do projeto a configurar; por padrão, o diretório atual."),
) -> None:
    """Detecta a stack e gera runners e regras de ambiente específicos do projeto.
    Não instala dependências nem executa testes, permitindo revisão antes de ações externas.
    """
    target = project.expanduser().resolve()
    if target.exists() and not target.is_dir():
        typer.echo(f"Erro: o destino não é um diretório: {target}", err=True)
        raise typer.Exit(1)
    target.mkdir(parents=True, exist_ok=True)
    if not config_path(target).exists():
        init_project(target)
    ensure_gitignore(target)
    stack = configure_project(target)
    ensure_stack_gitignore(target, stack["languages"])
    typer.echo(json.dumps({"stack": stack, "integrations": available_integrations()}, ensure_ascii=False, indent=2))


@app.command("test")
def test_all(
    suite: List[str] = typer.Option(None, "--suite", help="Executa somente as suítes informadas; pode repetir."),
    exclude: List[str] = typer.Option(None, "--exclude", help="Não executa as suítes informadas; pode repetir."),
    profile: Optional[str] = typer.Option(None, "--profile", help="Sobrescreve o perfil de testes desta execução."),
    approve_actions: bool = typer.Option(False, "--approve-actions", help="Autoriza suítes marcadas como caras ou mutáveis."),
) -> None:
    """Executa o alias global de testes e consolida todas as suítes configuradas.
    Inclui contratos, análise estática e runners com seus próprios ciclos de setup e cleanup.
    """
    process, result = run_tests(
        project_root(),
        include_suites=set(suite) if suite else None,
        exclude_suites=set(exclude or []),
        approve_actions=approve_actions,
        profile=profile,
    )
    typer.echo(process.stdout, nl=False)
    typer.echo(f"\nResultado: {result['status']}")
    typer.echo("Relatório visual: execute `looper draw serve` e abra /.looper/runs.html")
    if result["status"] != "passed":
        typer.echo(process.stderr, err=True)
        raise typer.Exit(process.returncode or 1)


@app.command("log")
def log_work(
    description: str = typer.Argument(..., help="Frase curta explicando o que foi feito."),
    bug: bool = typer.Option(False, "--bug", "-b", help="Marca o tipo de trabalho como bug."),
    teste: bool = typer.Option(False, "--test", "--teste", "-t", help="Marca o tipo de trabalho como teste."),
    implementacao: bool = typer.Option(False, "--impl", "--implementacao", "-i", help="Marca o tipo de trabalho como implementacao."),
    refactor: bool = typer.Option(False, "--refactor", "-r", help="Marca o tipo de trabalho como refactor."),
    work_type: List[str] = typer.Option(
        None,
        "--type",
        help="Tipo de trabalho em formato texto (bug, teste, implementacao, refactor).",
    ),
) -> None:
    """Registra uma alteração de código com estatísticas do Git em .looper/runs.
    Coleta flags de tipo e marca alterações incrementais grandes como retrabalho automaticamente.
    """
    types: list[str] = []
    if bug:
        types.append("bug")
    if teste:
        types.append("teste")
    if implementacao:
        types.append("implementacao")
    if refactor:
        types.append("refactor")
    if work_type:
        types.extend(work_type)

    try:
        created_file = record_run_entry(project_root(), description, types)
        typer.echo(f"Registro gravado em {created_file}")
    except ValueError as err:
        typer.echo(f"Erro: {err}", err=True)
        raise typer.Exit(1)


@backlog_app.command("generate")
def backlog_generate() -> None:
    """Reconstrói o backlog único preservando seu progresso."""
    try:
        typer.echo(json.dumps(generate_backlog(project_root()), ensure_ascii=False, indent=2))
    except (OSError, ValueError) as error:
        typer.echo(f"Erro: {error}", err=True)
        raise typer.Exit(1)


@backlog_app.command("missing")
def backlog_missing() -> None:
    """Retorna todas as tasks que ainda não estão concluídas."""
    try:
        typer.echo(json.dumps(missing_backlog(project_root()), ensure_ascii=False, indent=2))
    except (OSError, ValueError) as error:
        typer.echo(f"Erro: {error}", err=True)
        raise typer.Exit(1)


@backlog_app.command("task")
def backlog_task(
    interval: Optional[int] = typer.Option(None, "--interval", "--verification-interval", help="Sobrescreve o intervalo de nós para injeção de tarefas de verificação."),
    layer: Optional[str] = typer.Option(None, "--layer", help="Filtra a entrega: frontend, backend ou all."),
    frontend: bool = typer.Option(False, "--frontend", help="Entrega somente tasks frontend/L2."),
    backend: bool = typer.Option(False, "--backend", help="Entrega somente tasks backend/L3."),
) -> None:
    """Entrega uma única task e a reserva para o agente atual.
    Exibe somente o contexto acionável em linguagem humana.
    """
    try:
        if frontend and backend:
            raise ValueError("--frontend e --backend não podem ser usados juntos")
        selected_layer = "frontend" if frontend else "backend" if backend else layer
        response = next_backlog_task(project_root(), verification_interval=interval, layer=selected_layer)
        typer.echo(_format_backlog_response(response))
    except (OSError, ValueError) as error:
        typer.echo(f"Erro: {error}", err=True)
        raise typer.Exit(1)


@backlog_app.command("frontend")
def backlog_frontend(
    interval: Optional[int] = typer.Option(None, "--interval", "--verification-interval", help="Sobrescreve o intervalo de nós para injeção de tarefas de verificação."),
) -> None:
    """Entrega a próxima task frontend (nível 2 — telas/views)."""
    try:
        response = next_backlog_task(project_root(), verification_interval=interval, layer="frontend")
        typer.echo(_format_backlog_response(response))
    except (OSError, ValueError) as error:
        typer.echo(f"Erro: {error}", err=True)
        raise typer.Exit(1)


@backlog_app.command("backend")
def backlog_backend(
    interval: Optional[int] = typer.Option(None, "--interval", "--verification-interval", help="Sobrescreve o intervalo de nós L3 para injeção de tarefas de verificação."),
) -> None:
    """Entrega a próxima task backend (nível 3 — controllers, rules, models e integrações)."""
    try:
        response = next_backlog_task(project_root(), verification_interval=interval, layer="backend")
        typer.echo(_format_backlog_response(response))
    except (OSError, ValueError) as error:
        typer.echo(f"Erro: {error}", err=True)
        raise typer.Exit(1)


@backlog_app.command("config")
def backlog_config(
    interval: Optional[int] = typer.Option(None, "--interval", "--verification-interval", help="Define o intervalo de nós L2 para injeção de tarefas de verificação."),
    bootstrap: Optional[bool] = typer.Option(None, "--bootstrap/--no-bootstrap", help="Habilita ou desabilita a task de bootstrap inicial."),
    final_verification: Optional[bool] = typer.Option(None, "--final-verification/--no-final-verification", help="Habilita ou desabilita a task de verificação final E2E."),
    task_batch_size: Optional[int] = typer.Option(None, "--task-batch-size", min=1, max=5, help="Quantidade de tasks entregues no lote (1 a 5)."),
    l4_group_size: Optional[int] = typer.Option(None, "--l4-group-size", min=1, max=50, help="Quantidade de nós L4 entregues junto com cada pai L3 (1 a 50)."),
    task_batch_scope: Optional[str] = typer.Option(None, "--task-batch-scope", help="Escopo do lote: task ou node."),
    task_delivery_scope: Optional[str] = typer.Option(None, "--task-delivery-scope", help="Escopo comum de testes e implementação: task ou node (tela e funcionamento com os subfluxos)."),
    development_mode: Optional[str] = typer.Option(None, "--development-mode", help="Ordem arquitetural: sequential ou separated (frontend L2 antes de backend L3)."),
    min_task_interval_seconds: Optional[int] = typer.Option(None, "--min-task-interval-seconds", min=0, help="Janela mínima anti-script entre avanços."),
    test_loop_enabled: Optional[bool] = typer.Option(None, "--test-loop/--no-test-loop", help="Habilita ou desabilita o loop de testes."),
    test_loop_mode: Optional[str] = typer.Option(None, "--test-loop-mode", help="Preset do loop de testes."),
    implementation_loop_mode: Optional[str] = typer.Option(None, "--implementation-loop-mode", help="Preset do loop de implementação."),
    test_batch_size: Optional[int] = typer.Option(None, "--test-batch-size", min=1, help="Quantidade de unidades por avanço no loop de testes."),
    implementation_batch_size: Optional[int] = typer.Option(None, "--implementation-batch-size", min=1, help="Quantidade de unidades por avanço no loop de implementação."),
    l2_children_mode: Optional[str] = typer.Option(None, "--l2-children-mode", help="Filhos L3 no L2: none, context ou owned."),
    l3_loop_enabled: Optional[bool] = typer.Option(None, "--l3-loop/--no-l3-loop", help="Habilita ou desabilita o loop L3."),
    l3_include_parent: Optional[bool] = typer.Option(None, "--l3-parent-context/--no-l3-parent-context", help="Inclui o L2 pai no contexto do L3."),
    review_enabled: Optional[bool] = typer.Option(None, "--review/--no-review", help="Habilita ou desabilita a revisão automática por subagente."),
) -> None:
    """Exibe ou atualiza as configurações do backlog em .looper/config.yaml."""
    try:
        root = project_root()
        if interval is not None or bootstrap is not None or final_verification is not None or task_batch_size is not None or l4_group_size is not None or task_batch_scope is not None or task_delivery_scope is not None or development_mode is not None or min_task_interval_seconds is not None or test_loop_enabled is not None or test_loop_mode is not None or implementation_loop_mode is not None or test_batch_size is not None or implementation_batch_size is not None or l2_children_mode is not None or l3_loop_enabled is not None or l3_include_parent is not None or review_enabled is not None:
            if review_enabled is not None:
                set_review_enabled(root, review_enabled)
            updated = set_backlog_config(
                root,
                verification_interval=interval,
                bootstrap_task=bootstrap,
                final_verification_task=final_verification,
                task_batch_size=task_batch_size,
                l4_group_size=l4_group_size,
                task_batch_scope=task_batch_scope,
                task_delivery_scope=task_delivery_scope,
                development_mode=development_mode,
                min_task_interval_seconds=min_task_interval_seconds,
                test_loop_enabled=test_loop_enabled,
                test_loop_mode=test_loop_mode,
                implementation_loop_mode=implementation_loop_mode,
                test_batch_size=test_batch_size,
                implementation_batch_size=implementation_batch_size,
                l2_children_mode=l2_children_mode,
                l3_loop_enabled=l3_loop_enabled,
                l3_include_parent=l3_include_parent,
            )
            if review_enabled is not None:
                updated["review_enabled"] = review_enabled
            typer.echo(f"Configuração do backlog atualizada: {json.dumps(updated, ensure_ascii=False)}")
        else:
            current = get_backlog_config(root)
            typer.echo(json.dumps(current, ensure_ascii=False, indent=2))
    except (OSError, ValueError) as error:
        typer.echo(f"Erro: {error}", err=True)
        raise typer.Exit(1)


@backlog_app.command("test")
def backlog_test(
    layer: Optional[str] = typer.Option(None, "--layer", help="Filtra a entrega: frontend, backend ou all."),
    frontend: bool = typer.Option(False, "--frontend", help="Entrega somente testes frontend/L2."),
    backend: bool = typer.Option(False, "--backend", help="Entrega somente testes backend/L3."),
) -> None:
    """Entrega uma task incremental para criação dos testes do nó e subfluxos."""
    try:
        if frontend and backend:
            raise ValueError("--frontend e --backend não podem ser usados juntos")
        selected_layer = "frontend" if frontend else "backend" if backend else layer
        typer.echo(_format_backlog_response(next_backlog_test(project_root(), layer=selected_layer)))
    except (OSError, ValueError) as error:
        typer.echo(f"Erro: {error}", err=True)
        raise typer.Exit(1)


@backlog_app.command("change")
def backlog_change(
    layer: Optional[str] = typer.Option(None, "--layer", help="Filtra a entrega: frontend, backend ou all."),
    frontend: bool = typer.Option(False, "--frontend", help="Entrega somente alterações frontend/L2."),
    backend: bool = typer.Option(False, "--backend", help="Entrega somente alterações backend/L3."),
) -> None:
    """Entrega um pedido de alteração registrado no ícone de loop de um nó."""
    try:
        if frontend and backend:
            raise ValueError("--frontend e --backend não podem ser usados juntos")
        selected_layer = "frontend" if frontend else "backend" if backend else layer
        typer.echo(_format_backlog_response(next_backlog_change(project_root(), layer=selected_layer)))
    except (OSError, ValueError) as error:
        typer.echo(f"Erro: {error}", err=True)
        raise typer.Exit(1)


@backlog_app.command("complete")
def backlog_complete(task_id: str = typer.Argument(..., help="ID da task atualmente em andamento.")) -> None:
    """Conclui a task atual e avança o cursor da jornada em linguagem natural."""
    try:
        root = project_root()
        response = complete_backlog_task(root, task_id)
        review = maybe_review_completed_task(root, response)
        output = _format_backlog_response(response)
        if review:
            if review["status"] == "changes_created":
                output += f"\nRevisão concluída: {len(review['changes'])} change(s) registrada(s) para o próximo loop de alterações."
            elif review["status"] == "approved":
                output += "\nRevisão concluída: nenhuma lacuna foi encontrada; a task está aprovada."
            else:
                output += "\nRevisão não concluída: a task permanece concluída e a revisão pode ser repetida."
        typer.echo(output)
    except (OSError, ValueError) as error:
        typer.echo(f"Erro: {error}", err=True)
        raise typer.Exit(1)


@backlog_app.command("review")
def backlog_review(
    task_id: str = typer.Argument(..., help="ID da task concluída que será revisada."),
    agent: Optional[str] = typer.Option(None, "--agent", help="codex, claude ou antigravity."),
    scope: Optional[str] = typer.Option(None, "--scope", help="l2, l3, l2_and_l3 ou all."),
    model: Optional[str] = typer.Option(None, "--model"),
    reasoning: Optional[str] = typer.Option(None, "--reasoning"),
) -> None:
    """Revisa uma task concluída e cria changes pendentes quando necessário."""
    try:
        root = project_root()
        response = generate_backlog(root)
        task = next((item for item in response.get("tasks", []) if item.get("id") == task_id), None)
        if task is None:
            raise ValueError("task-id não existe no backlog")
        result = run_review(root, task, agent=agent, scope=scope, model=model, reasoning=reasoning)
        if result["status"] == "changes_created":
            typer.echo(f"Revisão concluída: {len(result['changes'])} change(s) registrada(s) para o próximo loop.")
        elif result["status"] == "approved":
            typer.echo("Revisão concluída: nenhuma lacuna foi encontrada; a task está aprovada.")
        else:
            typer.echo("Revisão pendente: o agente não concluiu; a task permanece concluída e pode ser revisada novamente.")
    except (OSError, ValueError) as error:
        typer.echo(f"Erro: {error}", err=True)
        raise typer.Exit(1)


@draw_change_app.command("add")
def draw_change_add(
    draw_id: str = typer.Option(..., "--draw-id"),
    node_id: int = typer.Option(..., "--node-id"),
    prompt: str = typer.Option(..., "--prompt"),
    review_id: Optional[str] = typer.Option(None, "--review-id"),
    task_id: Optional[str] = typer.Option(None, "--task-id"),
    agent: Optional[str] = typer.Option(None, "--agent"),
) -> None:
    """Cria uma change pendente no nó correspondente, em linguagem natural."""
    try:
        metadata = {key: value for key, value in {"source": "review", "review_id": review_id, "task_id": task_id, "agent": agent}.items() if value}
        created = add_draw_change(project_root(), draw_id, node_id, prompt, metadata=metadata)
        typer.echo(f"Change criada no Draw {draw_id}, nó {node_id}: {created['change']['prompt']}")
    except (OSError, ValueError) as error:
        typer.echo(f"Erro: {error}", err=True)
        raise typer.Exit(1)


@draw_app.command("create")
def draw_create(
    data_json: str = typer.Option(..., "--data-json", help="Payload JSON inline do desenho."),
) -> None:
    """Valida e grava somente o JSON de um desenho em .looper/draws.
    Atualiza o índice leve e nunca cria HTML individual para o desenho.
    """
    try:
        payload = json.loads(data_json)
        root = project_root()
        logical_payload = logical_draw_payload(payload)
        analysis = analyze_draw_structure(root, logical_payload)
        contract_warnings = analyze_draw_contract(
            logical_payload,
            f".looper/draws/{logical_payload.get('id', '(novo desenho)')}.json",
        )
        created = create_draw(root, payload)
    except (json.JSONDecodeError, ValueError) as error:
        typer.echo(f"Erro: {error}", err=True)
        raise typer.Exit(1)
    if analysis["warnings"]:
        summary = analysis["summary"]
        typer.echo(
            "Aviso: análise estrutural encontrou "
            f"{summary['warnings']} ocorrência(s) "
            f"({summary['exact_duplicates']} exata(s), {summary['near_duplicates']} próxima(s)); "
            "nenhum warning bloqueia a criação."
        )
        for warning in analysis["warnings"]:
            similarity = f"{warning['similarity']:.0%}"
            typer.echo(
                f"  - [{warning['structure']}] {warning['left']['source']} "
                f"({warning['left']['label']}) ↔ {warning['right']['source']} "
                f"({warning['right']['label']}): {warning['evidence']} ({similarity})."
            )
    for warning in contract_warnings:
        node_str = f" nó={warning['node_id']}" if warning.get("node_id") is not None else ""
        typer.echo(
            f"Aviso: [{warning['kind']}] {warning['file']}{node_str}: "
            f"{warning['evidence']} (mínimo {warning['limit']}); nenhum warning bloqueia a criação."
        )
    typer.echo(f"Desenho gravado em {created}")


@app.command("create")
def app_create(
    data_json: str = typer.Option(..., "--data-json", help="Payload JSON inline do desenho."),
) -> None:
    """Valida e grava somente o JSON de um desenho em .looper/draws."""
    draw_create(data_json=data_json)



@draw_app.command("list")
def draw_list() -> None:
    """Lista os desenhos disponíveis sem carregar seus grafos completos.
    Lê somente os metadados de .looper/draws/index.json.
    """
    try:
        entries = read_draw_index(project_root()).get("draws", [])
    except ValueError as error:
        typer.echo(f"Erro: {error}", err=True)
        raise typer.Exit(1)
    if not entries:
        typer.echo("Nenhum desenho disponível.")
        return
    for entry in entries:
        typer.echo(f"{entry['id']}\t{entry.get('title', '')}\t{entry.get('node_count', 0)} nós\t{entry.get('edge_count', 0)} relações")


@draw_app.command("symbols")
def draw_symbols() -> None:
    """Lista símbolos dos nós implementáveis sem executar testes ou análise completa."""
    report = collect_draw_symbols(project_root())
    typer.echo(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "passed":
        raise typer.Exit(1)


@draw_app.command("questions")
def draw_questions(
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Tag a filtrar (@looper, @obs, @developer, ou todas por padrão)."),
    answered: bool = typer.Option(False, "--answered", help="Inclui respostas; para observações use com --tag obs."),
) -> None:
    """Localiza perguntas ou anotações abertas marcadas com @looper, @obs ou @developer."""
    try:
        questions = find_addressed_questions(project_root(), tag=tag, answered=answered)
    except (OSError, ValueError, RuntimeError) as error:
        typer.echo(f"Erro: {error}", err=True)
        raise typer.Exit(1)
    typer.echo(json.dumps(questions, ensure_ascii=False, indent=2))


@draw_app.command("answer")
def draw_answer(
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Tag a filtrar (@looper, @obs, @developer, ou todas por padrão)."),
) -> None:
    """Entrega perguntas e observações pendentes em linguagem humana, agrupadas por Draw e nó.
    Mostra símbolos associados, arquivos, evidências e limitações sem despejar JSON.
    """
    try:
        # A saída humana histórica continua podendo revisar todas as menções;
        # o comando canônico de pendências é `draw questions`.
        questions = find_addressed_questions(project_root(), tag=tag or "all")
    except (OSError, ValueError, RuntimeError) as error:
        typer.echo(f"Erro: {error}", err=True)
        raise typer.Exit(1)
    typer.echo(format_draw_answers(questions, tag=tag))


@draw_app.command("consume-observation")
@draw_app.command("consume-obs")
def draw_consume_observation(
    draw_id: str = typer.Option(..., "--draw-id", help="ID do Draw que contém a observação."),
    question_id: int = typer.Option(..., "--question-id", help="ID numérico da pergunta respondida."),
    node_id: Optional[int] = typer.Option(None, "--node-id", help="Nó da observação; omita para pergunta geral."),
) -> None:
    """Consome explicitamente uma observação respondida e preserva sua resposta."""
    try:
        consumed = consume_observation(project_root(), draw_id, question_id, node_id)
    except (OSError, ValueError, RuntimeError) as error:
        typer.echo(f"Erro: {error}", err=True)
        raise typer.Exit(1)
    typer.echo(json.dumps({"status": "consumed", "observation": consumed}, ensure_ascii=False, indent=2))


@draw_app.command("diff")
def draw_diff(
    run_id: Optional[str] = typer.Option(None, "--run-id", help="ID do log histórico a consultar."),
) -> None:
    """Exibe mudanças atuais dos JSONs de Draws desde o último looper log.
    Com --run-id, consulta o diff histórico salvo naquele log.
    """
    root = project_root()
    if run_id is None:
        diff_stats, draws, _ = get_incremental_draw_diff(root)
        typer.echo("Alterações dos Draws desde o último log:")
        typer.echo(
            f"Arquivos: {diff_stats['files_changed']} · "
            f"Linhas: +{diff_stats['lines_added']} / -{diff_stats['lines_deleted']}"
        )
    else:
        diff_record = get_logged_draw_diff(root, run_id=run_id)
        if diff_record is None:
            typer.echo("Nenhum snapshot de Draw encontrado nos logs.")
            return
        typer.echo(f"Log: {diff_record['run_id']} · {diff_record['timestamp']}")
        draws = diff_record.get("draws", [])
    if not draws:
        message = (
            "Nenhuma alteração nos JSONs de Draws desde o último log."
            if run_id is None
            else "Nenhuma alteração nos JSONs de Draws neste log."
        )
        typer.echo(message)
        return
    for draw in draws:
        typer.echo(f"\n[{draw.get('status', 'changed')}] {draw.get('path', 'desenho desconhecido')}")
        typer.echo(str(draw.get("diff", "")))


@draw_app.command("improve")
def draw_improve(
    pending: bool = typer.Option(False, "--pending", help="Lista sessões completas aguardando aplicação."),
    create: bool = typer.Option(False, "--create", help="Cria ou atualiza uma sessão separada do Draw."),
    data_json: Optional[str] = typer.Option(None, "--data-json", help="Payload JSON da sessão de melhoria."),
    mark_applied: bool = typer.Option(False, "--mark-applied", help="Marca uma sessão pronta como aplicada."),
    improvement_id: Optional[str] = typer.Option(None, "--id", help="ID da sessão de melhoria."),
) -> None:
    """Coordena sessões de perguntas sem substituir o JSON do Draw associado.

    O agente usa --pending para consumir somente sessões com as dez respostas
    preenchidas. A alteração arquitetural continua sendo uma decisão do agente;
    este comando apenas persiste a sessão e seu estado de ciclo.
    """
    selected = sum((pending, create, mark_applied))
    if selected != 1:
        typer.echo("Erro: use exatamente uma entre --pending, --create ou --mark-applied.", err=True)
        raise typer.Exit(1)
    root = project_root()
    try:
        if pending:
            if data_json is not None or improvement_id is not None:
                raise ValueError("--pending não aceita --data-json nem --id")
            typer.echo(json.dumps(list_ready_improvements(root), ensure_ascii=False, indent=2))
            return
        if create:
            if data_json is None or improvement_id is not None:
                raise ValueError("--create exige --data-json e não aceita --id")
            payload = json.loads(data_json)
            output = create_improvement(root, payload)
            typer.echo(f"Sessão de melhoria gravada em {output.relative_to(root)}")
            return
        if data_json is not None:
            raise ValueError("--mark-applied não aceita --data-json")
        if not improvement_id:
            raise ValueError("--mark-applied exige --id")
        output = mark_improvement_applied(root, improvement_id)
        typer.echo(f"Sessão de melhoria aplicada em {output.relative_to(root)}")
    except (json.JSONDecodeError, OSError, ValueError) as error:
        typer.echo(f"Erro: {error}", err=True)
        raise typer.Exit(1)


@draw_app.command("associate-reference")
def draw_associate_reference(
    draw_id: str = typer.Option(..., "--draw-id", help="ID do desenho que contém o nó."),
    node_id: Optional[int] = typer.Option(None, "--node-id", help="ID numérico do nó para associação unitária."),
    qualified_name: Optional[str] = typer.Option(None, "--qualified-name", help="Símbolo qualificado da codebase."),
    source_dependency: List[str] = typer.Option(None, "--source-dependency", help="Símbolo qualificado relacionado; pode repetir."),
    batch_json: Optional[str] = typer.Option(None, "--batch-json", help="Lista JSON de associações unitárias."),
) -> None:
    """Associa um nó a símbolos qualificados sem calcular facts derivados."""
    try:
        if batch_json is not None:
            batch = json.loads(batch_json)
            output = associate_node_references(project_root(), draw_id, batch)
        else:
            if node_id is None or qualified_name is None:
                raise ValueError("node_id e qualified_name são obrigatórios fora do modo lote")
            output = associate_node_reference(project_root(), draw_id, node_id, qualified_name, source_dependency or [])
    except (json.JSONDecodeError, ValueError) as error:
        typer.echo(f"Erro: {error}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Referência associada em {output}")


@draw_app.command("serve")
def draw_serve(
    port: int = typer.Option(8765, "--port", min=1, max=65535, help="Porta local do viewer."),
) -> None:
    """Serve o viewer Draw localmente para carregar JSONs por fetch.
    Vincula o servidor a 127.0.0.1 e mantém o processo ativo até interrupção.
    """
    current_port = port
    try:
        while True:
            try:
                serve_draw(project_root(), port=current_port)
                return
            except OSError as error:
                if error.errno != errno.EADDRINUSE:
                    raise
                process_ids = listening_process_ids(current_port)
                if process_ids and typer.confirm(
                    f"A porta {current_port} já está em uso. Deseja encerrar o outro servidor e iniciar um novo?",
                    default=False,
                ):
                    terminate_processes(process_ids)
                    typer.echo(f"Servidor(es) encerrado(s) na porta {current_port}. Tentando iniciar novamente...")
                    continue
                current_port = ask_alternative_port(current_port)
    except (RuntimeError, ValueError, OSError) as error:
        typer.echo(f"Erro: {error}", err=True)
        raise typer.Exit(1)


def listening_process_ids(port: int) -> tuple[int, ...]:
    """Obtém os processos que escutam TCP na porta informada, quando possível."""
    try:
        result = subprocess.run(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ()
    process_ids = []
    for value in result.stdout.splitlines():
        try:
            process_ids.append(int(value.strip()))
        except ValueError:
            continue
    return tuple(dict.fromkeys(process_ids))


def terminate_processes(process_ids: Iterable[int]) -> None:
    """Solicita encerramento aos processos identificados pelo sistema operacional."""
    for process_id in process_ids:
        if process_id == os.getpid():
            raise RuntimeError("o processo atual não pode ser encerrado")
        try:
            os.kill(process_id, signal.SIGTERM)
        except ProcessLookupError:
            continue
        except PermissionError as error:
            raise RuntimeError(f"sem permissão para encerrar o processo {process_id}") from error


def ask_alternative_port(current_port: int) -> int:
    """Solicita uma porta alternativa válida e diferente da porta ocupada."""
    while True:
        alternative = typer.prompt(f"Informe outra porta para o viewer (a atual é {current_port})", type=int)
        if 1 <= alternative <= 65535 and alternative != current_port:
            return alternative
        typer.echo("Informe uma porta entre 1 e 65535, diferente da porta ocupada.", err=True)







if __name__ == "__main__":
    app()
