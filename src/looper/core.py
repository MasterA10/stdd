import difflib
import json
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .backlog import check_backlog
from .contract import check_contract
from .draw import ensure_draw_workspace
from .improvements import ensure_improvement_workspace
from .models import REWORK_LINE_THRESHOLD, RunLogEntry
from .runs import ensure_runs_workspace, update_runs_index, write_test_report
from .static_analysis import run_static_analysis, write_static_analysis_kpis
from .traceability import refresh_traceability
from .setup import ensure_design_document
from .reviews import ensure_review_workspace
from .config import DEFAULT_BACKEND_LOGGING_INSTRUCTION, config_path, load_config, save_config

VALID_WORK_TYPES = {"bug", "teste", "implementacao", "refactor"}
DEFAULT_CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".c", ".cpp",
    ".h", ".hpp", ".cs", ".rs", ".rb", ".php", ".swift", ".kt", ".scala",
    ".sh", ".bash",
}
GITIGNORE_RULES = (
    "# Looper managed rules",
    ".env",
    ".env.*",
    "!.env.example",
    "*.pyc",
    "__pycache__/",
    ".venv/",
    "venv/",
    "node_modules/",
    ".cache/",
    "**/.cache/",
    "*.cache",
    ".coverage",
    "coverage/",
    "htmlcov/",
    "._*",
    ".DS_Store",
    ".AppleDouble",
    ".LSOverride",
    "Icon\r",
)
INTERNAL_STATE_DIRECTORIES = {".looper"}
LEGACY_REFERENCE_PATTERN = re.compile(r"stdd", re.IGNORECASE)
LEGACY_MIGRATION_IGNORED_PARTS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "vendor",
    "build",
    "dist",
    "coverage",
    "htmlcov",
    "__pycache__",
    ".pytest_cache",
    "tests",
    "src",
    ".agents",
    ".claude",
    ".gemini",
}
LEGACY_MIGRATION_IGNORED_FILES = {".env", ".env.local", ".env.production", ".env.development"}


def get_tracked_extensions(root: Path) -> set[str]:
    """Retorna o conjunto de extensões de arquivo rastreadas na medição de diff.
    Lê a propriedade tracked_extensions de .looper/config.json ou utiliza os valores padrão.
    """
    path = config_path(root)
    if path.exists() or (looper_dir(root) / "config.json").exists():
        try:
            config = load_config(root)
            custom_extensions = config.get("tracked_extensions")
            if isinstance(custom_extensions, list) and custom_extensions:
                return {
                    ext.strip().lower() if ext.startswith(".") else f".{ext.strip().lower()}"
                    for ext in custom_extensions
                    if isinstance(ext, str) and ext.strip()
                }
        except Exception:
            pass
    return DEFAULT_CODE_EXTENSIONS


def project_root(path: Path | None = None) -> Path:
    """Retorna o caminho absoluto do diretório raiz do projeto.
    Resolve o caminho recebido por parâmetro ou o diretório atual do sistema.
    """
    return (path or Path.cwd()).resolve()


def looper_dir(root: Path) -> Path:
    """Retorna o diretório de estado interno .looper.
    Concatena o caminho da raiz informada com a pasta reservada .looper.
    """
    return root / ".looper"


def _replace_legacy_reference(match: re.Match[str]) -> str:
    """Troca LOOPER por Looper preservando a capitalização mais comum."""
    value = match.group(0)
    if value.isupper():
        return "LOOPER"
    if value[:1].isupper():
        return "Looper"
    return "looper"


def _append_unique(paths: list[Path], path: Path) -> None:
    if path not in paths:
        paths.append(path)


def _merge_legacy_state(legacy: Path, current: Path, changed: list[Path]) -> None:
    """Move somente itens ausentes quando os estados antigo e atual coexistem."""
    entries = sorted(
        legacy.rglob("*"),
        key=lambda path: (len(path.relative_to(legacy).parts), path.as_posix()),
    )
    for source in entries:
        if source.is_symlink():
            continue
        destination = current / source.relative_to(legacy)
        if source.is_dir():
            if not destination.exists():
                destination.mkdir(parents=True)
                _append_unique(changed, destination)
            continue
        if source.is_file() and not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            source.replace(destination)
            _append_unique(changed, destination)

    for directory in sorted(
        (path for path in legacy.rglob("*") if path.is_dir() and not path.is_symlink()),
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        try:
            directory.rmdir()
        except OSError:
            pass
    try:
        legacy.rmdir()
    except OSError:
        pass


def _legacy_text_files(root: Path):
    for path in root.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        relative_parts = path.relative_to(root).parts
        if LEGACY_MIGRATION_IGNORED_PARTS.intersection(relative_parts):
            continue
        if path.name in LEGACY_MIGRATION_IGNORED_FILES:
            continue
        yield path


def migrate_legacy_project(root: Path) -> list[Path]:
    """Migra o estado `.looper` e referências textuais antigas para o Looper.

    A migração é executada pelo ``looper init``. Um estado legado é renomeado
    quando `.looper` ainda não existe. Se ambos existirem, somente arquivos que
    não estão presentes no estado atual são incorporados; conflitos ficam
    preservados no local antigo para evitar perda silenciosa de dados.
    """
    changed: list[Path] = []
    legacy = root / ".stdd"
    current = looper_dir(root)
    if legacy.is_dir() and not legacy.is_symlink():
        if not current.exists():
            legacy.rename(current)
            _append_unique(changed, current)
        elif current.is_dir():
            _merge_legacy_state(legacy, current, changed)

    for path in _legacy_text_files(root):
        try:
            content = path.read_bytes()
            if b"stdd" not in content.lower() or b"\x00" in content:
                continue
            text = content.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        updated = LEGACY_REFERENCE_PATTERN.sub(_replace_legacy_reference, text)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            _append_unique(changed, path)
    return changed


AGENT_SKILL_DIRECTORIES = {
    "codex": ".agents/skills",
    "claude": ".claude/skills",
    "gemini": ".gemini/skills",
}

RETIRED_AGENT_SKILLS = {
    "implement",
    "implement-backlog",
    "create-tests",
    "create-tests-backlog",
    "e2e-tester",
    "feature",
}

AGENT_INSTRUCTION_FILES = {
    "codex": ("AGENTS.md",),
    "claude": ("CLAUDE.md", ".claude/CLAUDE.md"),
    "gemini": ("GEMINI.md",),
}
Looper_AGENT_BLOCK_START = "<!-- Looper:BEGIN AGENT INSTRUCTIONS -->"
Looper_AGENT_BLOCK_END = "<!-- Looper:END AGENT INSTRUCTIONS -->"
_LOOPER_AGENT_SHARED_BLOCK = f"""{Looper_AGENT_BLOCK_START}
## Looper — Harness Control Layer

Este projeto usa o Looper para especificação, implementação, testes e evidências.

- Registre cada trabalho concluído com `looper log \"descrição curta\" --type implementacao|teste|bug|refactor`.
- Execute `looper test` antes de declarar uma tarefa concluída e trate falhas como bloqueios.
- Preserve o contrato existente, os testes aprovados e os arquivos protegidos.
- Use `.looper/` para configuração, desenhos, execuções e evidências; não registre segredos nos logs.
- A análise de código deve permanecer separada da análise dos Draws/JSONs; preserve símbolos, referências e métricas gerais quando a stack oferecer essa capacidade.
- Antes de qualquer commit ou push na branch `main`, confirme que o diff inclui as fontes, templates, skills, assets empacotados, README e testes necessários para o comando de instalação do README reproduzir a versão publicada.
- Depois de alterar o framework, valide a instalação equivalente com `uv tool install --force --editable .` e confirme que `looper init` instala as skills atuais; não publique somente uma parte da alteração.
- Ao integrar APIs/apps externos, registre o contrato no `AGENTS.md` e consulte a documentação oficial antes de implementar.
- O `.looper/design.md` é a fonte obrigatória de decisões visuais: consulte e respeite identidade, tipografia, espaçamento, estados, acessibilidade e contraste em qualquer alteração ou implementação de interface; seu preenchimento é obrigatório antes de liberar o bootstrap.
- Ao construir, refinar ou revisar interfaces, leia e use a skill `$open-design` instalada em `.agents/skills/open-design/SKILL.md`, consultando seus recursos sob demanda.
- Mantenha memória contextual seletiva: registre decisões duráveis e aceitas no `AGENTS.md` (contratos, arquitetura, operação e escopo) ou no `.looper/design.md` (visual e interação); consolide duplicatas e não registre hipóteses, detalhes temporários, IDs de execução ou segredos.
- `$test-application` lê o Draw completo, propõe e implementa uma suíte de testes transversal (incluindo Playwright e persistência quando aplicáveis); `$implement-frontend` e `$implement-backend` continuam pertencendo aos loops acionados por `looper backlog frontend`, `looper backlog backend` e `looper backlog task`.
- Quando o pedido vier de uma interação comum, trate-o como interação comum e siga somente as instruções necessárias ao pedido; não transforme a edição em task de backlog nem exija o ciclo de testes/implementação do backlog sem que o cursor tenha entregue uma task.
- No loop do backlog, execute `looper backlog complete <task-id>` com o mesmo ID recebido somente após validar a task; sem isso, o cursor não avança.
- Quando o backlog entregar o nó e os subfluxos internos juntos, implemente e teste ambos; “Tela” classifica o nível do nó e não limita a entrega ao frontend.
- Ao relatar o resultado, informe status, arquivos alterados, testes executados, evidências e limitações.
{{mode_instruction}}
{Looper_AGENT_BLOCK_END}"""
_Looper_AGENT_BLOCK_PATTERN = re.compile(
    rf"{re.escape(Looper_AGENT_BLOCK_START)}.*?{re.escape(Looper_AGENT_BLOCK_END)}\n?",
    re.DOTALL,
)


def _agent_mode_instruction(development_mode: str) -> str:
    """Renderiza a regra arquitetural persistida no bloco do agente."""
    if development_mode == "separated":
        return (
            "### Estratégia de desenvolvimento do backlog\n\n"
            "- O modo é separado: conclua todos os nós L2 como frontend/view antes de liberar qualquer L3.\n"
            "- Nas tasks L2, implemente a tela, estados, interações e links/transições entre telas; não implemente controller, model, regra de negócio, persistência ou integrações de backend.\n"
            "- Nas tasks L3, implemente o backend/controller/model e seus testes; o loop de testes não cria testes para L2.\n"
            "- Os filtros `--frontend` e `--backend` são transitórios e não concluem a outra camada."
        )
    return (
        "### Estratégia de desenvolvimento do backlog\n\n"
        "- O modo é conjunto: cada task segue a ordem do cursor e implementa a tela/view e o comportamento funcional descritos no nó e nos subfluxos.\n"
        "- Preserve a navegação entre telas e implemente as camadas de backend quando elas fizerem parte do escopo entregue.\n"
        "- Os filtros `--frontend` e `--backend` permitem consultar uma camada por vez sem alterar a ordem ou concluir o restante do backlog."
    )


def _agent_block(development_mode: str | None = None) -> str:
    """Monta o bloco gerenciado pelo Looper para o modo efetivo."""
    mode = development_mode if development_mode in {"sequential", "separated"} else "sequential"
    return _LOOPER_AGENT_SHARED_BLOCK.replace("{mode_instruction}", _agent_mode_instruction(mode))


Looper_AGENT_BLOCK = _agent_block("sequential")


def ensure_agent_instructions(root: Path, integrations: tuple[str, ...], development_mode: str | None = None) -> list[Path]:
    """Instala instruções locais do Looper nos arquivos reconhecidos por cada agente.
    Cria ou atualiza AGENTS.md, CLAUDE.md e GEMINI.md sem tocar em arquivos globais e sem duplicar o bloco.
    """
    changed: list[Path] = []
    for integration in integrations:
        candidates = AGENT_INSTRUCTION_FILES[integration]
        instruction_path = next(
            (root / candidate for candidate in candidates if (root / candidate).is_file()),
            root / candidates[0],
        )
        existing = instruction_path.read_text(encoding="utf-8") if instruction_path.exists() else ""
        without_looper = _Looper_AGENT_BLOCK_PATTERN.sub("", existing).lstrip("\n")
        updated = _agent_block(development_mode) + ("\n\n" + without_looper if without_looper else "\n")
        if updated != existing:
            instruction_path.parent.mkdir(parents=True, exist_ok=True)
            instruction_path.write_text(updated, encoding="utf-8")
            changed.append(instruction_path)
    return changed


def _resolve_init_development_mode(config: Path, requested: str | None) -> tuple[str, bool]:
    """Lê, normaliza e persiste o modo antes de instalar instruções de agente."""
    try:
        config_data = load_config(config.parent.parent)
    except (OSError, UnicodeError, ValueError):
        config_data = {}
        config_data = {}
    backlog_config = config_data.setdefault("backlog", {})
    if not isinstance(backlog_config, dict):
        backlog_config = {}
        config_data["backlog"] = backlog_config
    mode = requested if requested in {"sequential", "separated"} else backlog_config.get("development_mode")
    if mode not in {"sequential", "separated"}:
        mode = "sequential"
    changed = backlog_config.get("development_mode") != mode
    if changed:
        backlog_config["development_mode"] = mode
        save_config(config.parent.parent, config_data)
    return mode, changed


def init_project(root: Path, integrations: tuple[str, ...] = ("codex",), development_mode: str | None = None) -> list[Path]:
    """Inicializa a estrutura do projeto e instala as skills dos agentes.
    Cria as pastas internas de execuções/features e copia os templates Markdown para .agents/skills.
    """
    created: list[Path] = migrate_legacy_project(root)
    for directory in (
        looper_dir(root) / "runs",
        looper_dir(root) / "features",
        *(root / AGENT_SKILL_DIRECTORIES[integration] for integration in integrations),
    ):
        if not directory.exists():
            directory.mkdir(parents=True)
            created.append(directory)

    config = config_path(root)
    if not config.exists():
        save_config(root, {
                    "test_commands": [],
                    "testing": {"profile": "mvp"},
                    "contract": {
                        "enabled": True,
                        "code_language": "python",
                        "description_language": "pt-BR",
                        "short_description_max_chars": 160,
                    },
                    "static_analysis": {
                        "enabled": True,
                        "adapter_command": None,
                        "contract_version": "1",
                        "allow_marked_test_credentials": True,
                        "exceptions": [],
                        "quality": {
                            "functions": {
                                "max_lines": {"warning": 100, "blocking": 150},
                                "max_complexity": {"warning": 10, "blocking": 25},
                            },
                            "tests": {
                                "max_lines": {"warning": 80, "blocking": 160},
                            },
                        },
                    },
                    "tracked_extensions": sorted(list(DEFAULT_CODE_EXTENSIONS)),
                    "backlog": {
                        "test_loop_enabled": True,
                        "bootstrap_task": True,
                        "bootstrap_opt_out": False,
                        "l2_verification_interval": 0,
                        "final_verification_task": False,
                        "task_batch_size": 1,
                        "task_batch_scope": "task",
                        "task_delivery_scope": "task",
                        "development_mode": "sequential",
                        "test_loop": {
                            "mode": "task_order",
                            "batch_size": 1,
                            "include_level_2": True,
                            "l2_children_mode": "none",
                            "l3_loop_enabled": True,
                            "l3_include_parent": True,
                        },
                        "implementation_loop": {
                            "mode": "task_order",
                            "batch_size": 1,
                            "l2_children_mode": "none",
                            "l3_loop_enabled": True,
                            "l3_include_parent": True,
                        },
                        "min_task_interval_seconds": 0,
                        "l2_post_verification_tasks": False,
                        "level_2_meaning": "Tela",
                        "level_3_meaning": "Regra de negócio e detalhes da tela",
                    },
                    "version": 1,
                })
        created.append(config)

    created.extend(ensure_static_analysis_defaults(config))

    created.extend(ensure_draw_workspace(root, include_example=True))
    created.extend(ensure_improvement_workspace(root))
    created.extend(ensure_runs_workspace(root))
    data = load_config(root)
    changed = False
    if "instructions" not in data:
        data["instructions"] = {"backend": DEFAULT_BACKEND_LOGGING_INSTRUCTION, "frontend": "", "change": ""}
        changed = True
    if "review" not in data:
        data["review"] = {}
        changed = True
    if changed:
        save_config(root, data)
        created.append(config)
    created.extend(ensure_review_workspace(root))
    design_path = ensure_design_document(root)
    if design_path not in created:
        created.append(design_path)
    created.extend(ensure_gitignore(root))

    for integration in integrations:
        skill_dir = root / AGENT_SKILL_DIRECTORIES[integration]
        for retired in RETIRED_AGENT_SKILLS:
            retired_dir = skill_dir / retired
            if retired_dir.exists():
                shutil.rmtree(retired_dir, ignore_errors=True)
        for source in agent_templates():
            name = source.parent.name
            sources = [source]
            openai_metadata = source.parent / "agents" / "openai.yaml"
            if integration == "codex" and openai_metadata.exists():
                sources.append(openai_metadata)
            for skill_source in sources:
                relative = skill_source.relative_to(source.parent)
                target = skill_dir / name / relative
                source_text = skill_source.read_text(encoding="utf-8")
                if not target.exists() or target.read_text(encoding="utf-8") != source_text:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(source_text, encoding="utf-8")
                    if target not in created:
                        created.append(target)
    config_mode, config_changed = _resolve_init_development_mode(config, development_mode)
    if config_changed and config not in created:
        created.append(config)
    created.extend(ensure_agent_instructions(root, integrations, config_mode))
    return created


def ensure_static_analysis_defaults(config_path: Path) -> list[Path]:
    """Completa configurações antigas sem substituir escolhas existentes."""
    try:
        config_data = load_config(config_path.parent.parent)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return []
    if not isinstance(config_data, dict):
        return []
    static_config = config_data.get("static_analysis")
    if static_config is None:
        static_config = {}
        config_data["static_analysis"] = static_config
    if not isinstance(static_config, dict):
        return []
    changed = False
    if "frontend" in static_config:
        del static_config["frontend"]
        changed = True
    defaults = {
        "enabled": True,
        "adapter_command": None,
        "contract_version": "1",
        "allow_marked_test_credentials": True,
        "exceptions": [],
    }
    for key, value in defaults.items():
        if key not in static_config:
            static_config[key] = value
            changed = True
    if changed:
        save_config(config_path.parent.parent, config_data)
        return [config_path]
    return []


def ensure_gitignore(root: Path) -> list[Path]:
    """Adiciona regras seguras e idempotentes ao gitignore do projeto.
    Preserva regras existentes e evita versionar ambientes, caches Python e arquivos de ambiente.
    """
    path = root / ".gitignore"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = existing.splitlines()
    missing = [rule for rule in GITIGNORE_RULES if rule not in lines]
    if not missing:
        return []
    updated = existing
    if updated and not updated.endswith("\n"):
        updated += "\n"
    if updated and not updated.endswith("\n\n"):
        updated += "\n"
    updated += "\n".join(missing) + "\n"
    path.write_text(updated, encoding="utf-8")
    return [path]


def agent_templates() -> list[Path]:
    """Localiza os arquivos de template SKILL.md distribuídos com o pacote.
    Percorre o diretório de templates de agentes e retorna os caminhos em ordem alfabética.
    """
    templates = Path(__file__).parent / "templates" / "agents"
    return sorted(templates.glob("*/SKILL.md"))


def execute_test_suite(root: Path, suite: dict[str, Any]) -> tuple[subprocess.CompletedProcess, dict[str, Any]]:
    """Executa uma suíte configurada e normaliza falhas de processo ou timeout.
    Retorna evidência estruturada sem interromper as demais suítes do alias global.
    """
    name = str(suite.get("name") or "unnamed")
    command = suite.get("command")
    started = time.monotonic()
    if not isinstance(command, list) or not command or not all(isinstance(argument, str) for argument in command):
        process = subprocess.CompletedProcess(command or [], 2, "", "command deve ser uma lista não vazia de strings")
    else:
        try:
            process = subprocess.run(
                command,
                cwd=root,
                text=True,
                capture_output=True,
                timeout=suite.get("timeout"),
            )
        except subprocess.TimeoutExpired as error:
            stdout = error.stdout.decode() if isinstance(error.stdout, bytes) else (error.stdout or "")
            stderr = error.stderr.decode() if isinstance(error.stderr, bytes) else (error.stderr or "")
            process = subprocess.CompletedProcess(command, 124, stdout, stderr + "\ntimeout da suíte excedido")
        except OSError as error:
            process = subprocess.CompletedProcess(command, 127, "", f"não foi possível executar a suíte: {error}")
    duration = round(time.monotonic() - started, 6)
    report = {
        "name": name,
        "command": command,
        "exit_code": process.returncode,
        "status": "passed" if process.returncode == 0 else "failed",
        "duration_seconds": duration,
    }
    return process, report


def get_suite_skip_reason(
    suite: dict[str, Any],
    profile: str,
    include_suites: set[str] | None,
    exclude_suites: set[str],
    approve_actions: bool,
) -> str | None:
    """Decide deterministicamente se uma suíte deve ser pulada pelo alias global.
    Filtros explícitos prevalecem sobre perfil e enabled, mas nunca sobre aprovação obrigatória.
    """
    name = str(suite.get("name") or "unnamed")
    if name in exclude_suites:
        return "excluded"
    explicitly_included = include_suites is not None and name in include_suites
    if include_suites is not None and not explicitly_included:
        return "not_selected"
    if not explicitly_included:
        if suite.get("enabled") is False:
            return "disabled"
        profiles = suite.get("profiles")
        if isinstance(profiles, list) and profiles and profile not in profiles:
            return "profile_not_selected"
    if suite.get("requires_approval") is True and not approve_actions:
        return "approval_required"
    return None


def build_not_executed_suite_report(suite: dict[str, Any], reason: str) -> dict[str, Any]:
    """Cria evidência explícita para uma suíte não executada.
    Preserva nome e comando para que o usuário possa revisar e liberar a ação depois.
    """
    return {
        "name": str(suite.get("name") or "unnamed"),
        "command": suite.get("command"),
        "exit_code": None,
        "status": "not_executed",
        "duration_seconds": 0.0,
        "reason": reason,
    }


def _compact_output(value: str | None, limit: int = 1200) -> str:
    """Mantém mensagens úteis e omite dumps extensos de subprocessos."""
    text = (value or "").strip()
    if not text:
        return ""
    if len(text) <= limit and not (text.startswith("{") and text.endswith("}")):
        return text
    return f"<saída omitida: {len(text)} caracteres>"


def _static_analysis_summary(report: dict[str, Any]) -> dict[str, Any]:
    """Resume o contrato estático sem imprimir símbolos e dependências inteiros."""
    findings = report.get("quality_findings", [])
    findings = findings if isinstance(findings, list) else []
    blocking_findings = [
        {
            key: finding[key]
            for key in ("kind", "file", "draw_id", "node_id", "symbol_id")
            if key in finding
        }
        for finding in findings
        if isinstance(finding, dict) and finding.get("severity") == "blocking"
    ]
    return {
        "status": report.get("status"),
        "reason": report.get("reason"),
        "symbols": len(report.get("symbols", [])) if isinstance(report.get("symbols", []), list) else 0,
        "dependencies": len(report.get("dependencies", [])) if isinstance(report.get("dependencies", []), list) else 0,
        "quality_findings": len(findings),
        "blocking_findings": len(blocking_findings),
        "blocking_details": blocking_findings,
        "errors": len(report.get("errors", [])) if isinstance(report.get("errors", []), list) else 0,
    }


def run_tests(
    root: Path,
    include_suites: set[str] | None = None,
    exclude_suites: set[str] | None = None,
    approve_actions: bool = False,
    profile: str | None = None,
):
    """Executa contratos, análise estática e todas as suítes do alias global.
    Consolida evidências por suíte e continua a execução mesmo quando uma delas falha.
    """
    run_id = uuid.uuid4().hex

    config = load_config(root)
    configured = config.get("test_commands")
    if not configured and config.get("test_command"):
        configured = [{"name": "all", "command": config["test_command"]}]
    suites = configured or []
    active_profile = profile or config.get("testing", {}).get("profile", "mvp")
    excluded = exclude_suites or set()

    violations = check_contract(root)
    backlog_report = check_backlog(root)
    static_report = run_static_analysis(
        root,
        run_id,
        config,
        sorted(get_workspace_snapshot(root)),
    )
    write_static_analysis_kpis(root, static_report, config)
    # Um relatório estático pode conter fatos válidos mesmo quando o gate de
    # qualidade bloqueia a execução. Preserve os facts para rastreabilidade;
    # o status bloqueado continua sendo devolvido ao usuário e ao CI.
    if static_report["status"] in {"passed", "blocked"} and static_report.get("symbols"):
        refresh_traceability(root, static_report)
    output: list[str] = []
    errors: list[str] = []
    suite_reports: list[dict[str, Any]] = []
    exit_code = 1 if violations or static_report["status"] == "blocked" or backlog_report["status"] == "blocked" else 0
    if violations:
        output.append(f"[contract] status=blocked violations={len(violations)}")
    else:
        output.append("[contract] status=passed violations=0")
    output.append("[static-analysis] " + json.dumps(_static_analysis_summary(static_report), ensure_ascii=False))
    if static_report["status"] == "blocked":
        errors.append("[static-analysis] " + _compact_output("; ".join(static_report["errors"])))
    output.append("[backlog] " + json.dumps({key: value for key, value in backlog_report.items() if key != "remaining_task_ids"}, ensure_ascii=False))
    if backlog_report["status"] == "blocked":
        if backlog_report.get("missing_tests", 0):
            errors.append(
                f"[backlog] testes pendentes: {backlog_report['missing_tests']}"
                + (f"; tasks pendentes: {backlog_report['remaining']}" if backlog_report.get("remaining") else "")
            )
        else:
            errors.append(f"[backlog] tasks pendentes: {backlog_report['remaining']}")
    for suite in suites:
        skip_reason = get_suite_skip_reason(suite, active_profile, include_suites, excluded, approve_actions)
        if skip_reason:
            suite_report = build_not_executed_suite_report(suite, skip_reason)
            suite_reports.append(suite_report)
            hint = "; execute novamente com --approve-actions após confirmar" if skip_reason == "approval_required" else ""
            output.append(f"[{suite_report['name']}] status=not_executed reason={skip_reason}{hint}")
            if suite.get("required") is True and skip_reason == "approval_required":
                exit_code = exit_code or 1
            continue
        suite_process, suite_report = execute_test_suite(root, suite)
        suite_reports.append(suite_report)
        suite_output = _compact_output(suite_process.stdout)
        output.append(f"[{suite_report['name']}] status={suite_report['status']} exit_code={suite_report['exit_code']}" + (f" output={suite_output}" if suite_output else ""))
        suite_error = _compact_output(suite_process.stderr)
        if suite_error:
            errors.append(f"[{suite_report['name']}] {suite_error}")
        exit_code = exit_code or suite_process.returncode
    if not suites:
        output.append("[all] status=not_executed reason=setup_required")
        suite_reports.append(
            {
                "name": "all",
                "command": [],
                "status": "not_executed",
                "reason": "setup_required",
                "exit_code": None,
                "duration_seconds": 0,
            }
        )
        exit_code = 1
    summary = {
        "total": len(suite_reports),
        "passed": sum(1 for suite in suite_reports if suite["status"] == "passed"),
        "failed": sum(1 for suite in suite_reports if suite["status"] == "failed"),
        "not_executed": sum(1 for suite in suite_reports if suite["status"] == "not_executed"),
    }
    output.append("[global-summary] " + json.dumps(summary, ensure_ascii=False))
    process = subprocess.CompletedProcess(suites, exit_code, "\n".join(output), "\n".join(errors))
    result = {
        "run_id": run_id,
        "commands": [suite["command"] for suite in suites],
        "exit_code": process.returncode,
        "status": "passed" if process.returncode == 0 else "blocked",
        "contract_violations": violations,
        "backlog": backlog_report,
        "static_analysis": static_report,
        "suites": suite_reports,
        "summary": summary,
        "profile": active_profile,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    write_test_report(root, result)
    return process, result


def _parse_gitignore_dirs(root: Path) -> set[str]:
    """Lê o .gitignore e retorna os diretórios e arquivos para ignorar."""
    gitignore_path = root / ".gitignore"
    ignored_patterns = set()
    if gitignore_path.exists():
        try:
            lines = gitignore_path.read_text(encoding="utf-8").splitlines()
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("!"):
                    ignored_patterns.add(line)
        except Exception:
            pass
    return ignored_patterns


def _gitignored_paths(root: Path, relative_paths: list[str]) -> set[str]:
    """Resolve as regras atuais do ``.gitignore`` sem manter cache entre runs."""
    if not relative_paths:
        return set()
    ignored: set[str] = set()
    try:
        checked = subprocess.run(
            ["git", "check-ignore", "--no-index", "-z", "--stdin"],
            cwd=root,
            input="\0".join(relative_paths) + "\0",
            text=True,
            capture_output=True,
            check=False,
        )
        ignored.update(item for item in checked.stdout.split("\0") if item)

        # Dentro de um checkout, o Git já interpreta a precedência completa
        # das regras, inclusive padrões globais e exceções iniciadas por ``!``.
        # O fallback abaixo é somente para diretórios sem Git; aplicá-lo aqui
        # também faria um padrão como ``*`` ignorar arquivos liberados depois.
        worktree = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        if worktree.returncode == 0 and worktree.stdout.strip() == "true":
            return ignored
    except OSError:
        pass

    import fnmatch

    patterns = _parse_gitignore_dirs(root)
    ignored_directories = {pattern[:-1].rstrip("/") for pattern in patterns if pattern.endswith("/")}
    for relative_path in relative_paths:
        path = Path(relative_path)
        if any(part in ignored_directories for part in path.parts):
            ignored.add(relative_path)
            continue
        for pattern in patterns:
            if pattern.endswith("/"):
                continue
            candidate_pattern = pattern.lstrip("/")
            if fnmatch.fnmatch(relative_path, candidate_pattern) or fnmatch.fnmatch(path.name, candidate_pattern):
                ignored.add(relative_path)
                break
    return ignored


def _filter_snapshot_by_gitignore(root: Path, snapshot: dict[str, list[str]]) -> dict[str, list[str]]:
    """Aplica o ``.gitignore`` atual também à snapshot histórica."""
    ignored = _gitignored_paths(root, sorted(snapshot))
    return {path: lines for path, lines in snapshot.items() if path not in ignored}


def get_workspace_snapshot(root: Path) -> dict[str, list[str]]:
    """Mapeia os arquivos rastreados da codebase e seus conteúdos em linhas.
    Filtra extensões configuradas e exclui o estado operacional do Looper.
    """
    tracked_exts = get_tracked_extensions(root)
    ignored_dirs = {".git", ".venv", "venv", "node_modules", *INTERNAL_STATE_DIRECTORIES, ".pytest_cache", "__pycache__"}
    
    gitignore_patterns = _parse_gitignore_dirs(root)
    for pattern in gitignore_patterns:
        if pattern.endswith("/"):
            ignored_dirs.add(pattern[:-1].split("/")[-1])
            
    candidates = [
        path for path in sorted(root.rglob("*"))
        if path.is_file()
        and path.suffix.lower() in tracked_exts
        and not ignored_dirs.intersection(path.parts)
    ]
    relative_candidates = [path.relative_to(root).as_posix() for path in candidates]
    ignored_by_git = _gitignored_paths(root, relative_candidates)

    snapshot: dict[str, list[str]] = {}
    for path, rel_path in zip(candidates, relative_candidates):
        ignored_by_file = rel_path in ignored_by_git
        if not ignored_by_file:
            try:
                snapshot[rel_path] = path.read_text(encoding="utf-8").splitlines()
            except (UnicodeDecodeError, PermissionError):
                continue
    return snapshot


def get_draw_snapshot(root: Path) -> dict[str, list[str]]:
    """Mapeia somente os JSONs lógicos dos desenhos para o histórico de logs.
    Exclui o índice operacional e arquivos fora da pasta direta de Draws.
    """
    draws_dir = looper_dir(root) / "draws"
    snapshot: dict[str, list[str]] = {}
    if not draws_dir.is_dir():
        return snapshot
    for path in sorted(draws_dir.glob("*.json")):
        if path.name == "index.json":
            continue
        try:
            rel_path = str(path.relative_to(root))
            snapshot[rel_path] = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
    return snapshot


def build_unified_diff(path: str, previous: list[str], current: list[str]) -> str:
    """Gera o patch textual entre duas versões de um arquivo rastreado.
    Usa o formato unified diff com caminhos relativos estáveis para facilitar auditoria e leitura.
    """
    return "\n".join(
        difflib.unified_diff(
            previous,
            current,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm="",
        )
    )


def get_incremental_draw_diff(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, list[str]]]:
    """Compara os JSONs de Draws com o último ponto registrado por log.
    Não consulta GitHub, git diff ou arquivos de código da base.
    """
    previous_snapshot = get_previous_draw_snapshot(root)
    current_snapshot = get_draw_snapshot(root)
    total_added = 0
    total_deleted = 0
    detailed_draws: list[dict[str, Any]] = []
    all_keys = set(previous_snapshot.keys()) | set(current_snapshot.keys())

    for key in sorted(all_keys):
        previous_lines = previous_snapshot.get(key, [])
        current_lines = current_snapshot.get(key, [])
        if key not in previous_snapshot:
            status = "created"
        elif key not in current_snapshot:
            status = "deleted"
        elif previous_lines != current_lines:
            status = "modified"
        else:
            continue

        diff = build_unified_diff(key, previous_lines, current_lines)
        added = sum(1 for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
        deleted = sum(1 for line in diff.splitlines() if line.startswith("-") and not line.startswith("---"))
        total_added += added
        total_deleted += deleted
        detailed_draws.append({
            "path": key,
            "status": status,
            "lines_added": added,
            "lines_deleted": deleted,
            "diff": diff,
        })

    return {
        "incremental": True,
        "lines_added": total_added,
        "lines_deleted": total_deleted,
        "files_changed": len(detailed_draws),
    }, detailed_draws, current_snapshot



def get_incremental_diff_stats(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Calcula estatísticas agregadas e detalhadas por arquivo de código alterado na execução.
    Compara o estado atual com o snapshot da execução anterior e gera resumo e detalhamento.
    """
    previous_snapshot = _filter_snapshot_by_gitignore(root, get_previous_workspace_snapshot(root))

    current_snapshot = get_workspace_snapshot(root)

    total_added = 0
    total_deleted = 0
    detailed_files: list[dict[str, Any]] = []

    all_keys = set(previous_snapshot.keys()) | set(current_snapshot.keys())
    for key in sorted(all_keys):
        file_added = 0
        file_deleted = 0
        previous_lines = previous_snapshot.get(key, [])
        current_lines = current_snapshot.get(key, [])

        if key not in previous_snapshot:
            file_added = len(current_lines)
        elif key not in current_snapshot:
            file_deleted = len(previous_lines)
        else:
            if previous_lines != current_lines:
                diff = list(difflib.unified_diff(previous_lines, current_lines, lineterm=""))
                for line in diff:
                    if line.startswith("+") and not line.startswith("+++"):
                        file_added += 1
                    elif line.startswith("-") and not line.startswith("---"):
                        file_deleted += 1

        if file_added > 0 or file_deleted > 0:
            total_added += file_added
            total_deleted += file_deleted
            detailed_files.append(
                {
                    "path": key,
                    "lines_added": file_added,
                    "lines_deleted": file_deleted,
                    "diff": build_unified_diff(key, previous_lines, current_lines),
                }
            )

    diff_stats = {
        "incremental": True,
        "lines_added": total_added,
        "lines_deleted": total_deleted,
        "files_changed": len(detailed_files),
    }

    return diff_stats, detailed_files


def is_rework_diff(diff_stats: dict[str, Any]) -> bool:
    """Identifica uma alteração grande o bastante para ser classificada como retrabalho.
    Usa a soma de linhas adicionadas e removidas para manter a regra determinística e auditável.
    """
    lines_added = int(diff_stats.get("lines_added", 0))
    lines_deleted = int(diff_stats.get("lines_deleted", 0))
    return lines_added >= REWORK_LINE_THRESHOLD and lines_deleted >= REWORK_LINE_THRESHOLD


def get_previous_workspace_snapshot(root: Path) -> dict[str, list[str]]:
    """Lê o estado da última execução diretamente dos Snapshots diários.
    Não cria arquivo auxiliar e retorna vazio quando ainda não existe uma execução anterior.
    """
    candidates = sorted((looper_dir(root) / "runs").glob("*/*_snapshot.json"))
    latest: tuple[str, dict[str, list[str]]] | None = None
    for path in candidates:
        if path.parent.name == "data" or path.name.startswith("._"):
            continue
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        workspace = document.get("workspace_snapshot")
        runs = document.get("runs", [])
        timestamp = runs[-1].get("timestamp", "") if isinstance(runs, list) and runs and isinstance(runs[-1], dict) else ""
        if isinstance(workspace, dict) and (latest is None or timestamp >= latest[0]):
            latest = (timestamp, workspace)
    return latest[1] if latest else {}


def get_previous_draw_snapshot(root: Path) -> dict[str, list[str]]:
    """Lê o último snapshot exclusivo dos JSONs lógicos dos desenhos.
    Retorna vazio quando o histórico ainda não possui essa trilha.
    """
    candidates = sorted((looper_dir(root) / "runs").glob("*/*_snapshot.json"))
    latest: tuple[str, dict[str, list[str]]] | None = None
    for path in candidates:
        if path.parent.name == "data" or path.name.startswith("._"):
            continue
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        draws = document.get("draws_snapshot")
        runs = document.get("runs", [])
        timestamp = runs[-1].get("timestamp", "") if isinstance(runs, list) and runs and isinstance(runs[-1], dict) else ""
        if isinstance(draws, dict) and (latest is None or timestamp >= latest[0]):
            latest = (timestamp, draws)
    return latest[1] if latest else {}


def get_logged_draw_diff(root: Path, run_id: str | None = None) -> dict[str, Any] | None:
    """Retorna o diff de Draws armazenado em um ponto de log.
    Sem ID, seleciona a execução mais recente; nunca calcula o diff da codebase.
    """
    candidates = sorted((looper_dir(root) / "runs").glob("*/*_snapshot.json"))
    selected: dict[str, Any] | None = None
    for path in candidates:
        if path.parent.name == "data" or path.name.startswith("._"):
            continue
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        runs = document.get("runs", [])
        if not isinstance(runs, list):
            continue
        for run in runs:
            if not isinstance(run, dict) or not isinstance(run.get("run_id"), str):
                continue
            if run_id is not None and run["run_id"] != run_id:
                continue
            candidate = {
                "run_id": run["run_id"],
                "timestamp": run.get("timestamp", ""),
                "draws": run.get("draws", []),
            }
            if selected is None or str(candidate["timestamp"]) >= str(selected["timestamp"]):
                selected = candidate
    return selected


def record_run_entry(root: Path, description: str, work_types: list[str]) -> Path:
    """Cria o resumo e o snapshot detalhado do código na pasta .looper/runs/YYYY-MM-DD/.
    Valida os tipos de trabalho, calcula os diffs de código e grava os relatórios da execução.
    """
    if not description or not description.strip():
        raise ValueError("A descrição da alteração não pode ser vazia.")
    normalized_types = [t.strip().lower() for t in work_types if t and t.strip()]
    if not normalized_types:
        raise ValueError("Ao menos um tipo de trabalho deve ser informado (bug, teste, implementacao, refactor).")
    invalid_types = set(normalized_types) - VALID_WORK_TYPES
    if invalid_types:
        raise ValueError(
            f"Tipos de trabalho inválidos: {', '.join(sorted(invalid_types))}. Permitidos: bug, teste, implementacao, refactor."
        )

    run_id = uuid.uuid4().hex
    timestamp = datetime.now(timezone.utc).isoformat()
    diff_stats, detailed_files = get_incremental_diff_stats(root)
    draw_diff_stats, draw_diffs, draw_snapshot = get_incremental_draw_diff(root)
    checkpoint = not diff_stats.get("lines_added") and not diff_stats.get("lines_deleted")
    if get_previous_workspace_snapshot(root) and is_rework_diff(diff_stats) and "refactor" not in normalized_types:
        normalized_types.append("refactor")
    entry = RunLogEntry(
        run_id=run_id,
        timestamp=timestamp,
        description=description.strip(),
        work_types=normalized_types,
        diff_stats=diff_stats,
        checkpoint=checkpoint,
        detailed_files=detailed_files,
        workspace_snapshot=get_workspace_snapshot(root),
        draw_diff_stats=draw_diff_stats,
        draw_diffs=draw_diffs,
        draw_snapshot=draw_snapshot,
    )
    runs_dir = looper_dir(root) / "runs"
    summary_file = entry.write(runs_dir)
    update_runs_index(root, summary_file)
    return summary_file
