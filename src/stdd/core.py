import difflib
import json
import re
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
from .runs import ensure_runs_workspace, update_runs_index
from .static_analysis import run_static_analysis, write_static_analysis_kpis
from .traceability import refresh_traceability

VALID_WORK_TYPES = {"bug", "teste", "implementacao", "refactor"}
DEFAULT_CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".c", ".cpp",
    ".h", ".hpp", ".cs", ".rs", ".rb", ".php", ".swift", ".kt", ".scala",
    ".sh", ".bash",
}
GITIGNORE_RULES = (
    "# STDD managed rules",
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
INTERNAL_STATE_DIRECTORIES = {".stdd"}


def get_tracked_extensions(root: Path) -> set[str]:
    """Retorna o conjunto de extensões de arquivo rastreadas na medição de diff.
    Lê a propriedade tracked_extensions de .stdd/config.json ou utiliza os valores padrão.
    """
    config_path = stdd_dir(root) / "config.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
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


def stdd_dir(root: Path) -> Path:
    """Retorna o diretório de estado interno .stdd.
    Concatena o caminho da raiz informada com a pasta reservada .stdd.
    """
    return root / ".stdd"


AGENT_SKILL_DIRECTORIES = {
    "codex": ".agents/skills",
    "claude": ".claude/skills",
    "gemini": ".gemini/skills",
}

AGENT_INSTRUCTION_FILES = {
    "codex": ("AGENTS.md",),
    "claude": ("CLAUDE.md", ".claude/CLAUDE.md"),
    "gemini": ("GEMINI.md",),
}
STDD_AGENT_BLOCK_START = "<!-- STDD:BEGIN AGENT INSTRUCTIONS -->"
STDD_AGENT_BLOCK_END = "<!-- STDD:END AGENT INSTRUCTIONS -->"
STDD_AGENT_BLOCK = f"""{STDD_AGENT_BLOCK_START}
## STDD — Harness Control Layer

Este projeto usa o STDD para especificação, implementação, testes e evidências.

- Registre cada trabalho concluído com `stdd log \"descrição curta\" --type implementacao|teste|bug|refactor`.
- Execute `stdd test` antes de declarar uma tarefa concluída e trate falhas como bloqueios.
- Preserve o contrato existente, os testes aprovados e os arquivos protegidos.
- Use `.stdd/` para configuração, desenhos, execuções e evidências; não registre segredos nos logs.
- A análise de código deve permanecer separada da análise dos Draws/JSONs; preserve símbolos, referências e métricas gerais quando a stack oferecer essa capacidade.
- Antes de qualquer commit ou push na branch `main`, confirme que o diff inclui as fontes, templates, skills, assets empacotados, README e testes necessários para o comando de instalação do README reproduzir a versão publicada.
- Depois de alterar o framework, valide a instalação equivalente com `uv tool install --force --editable .` e confirme que `stdd init` instala as skills atuais; não publique somente uma parte da alteração.
- Ao relatar o resultado, informe status, arquivos alterados, testes executados, evidências e limitações.
{STDD_AGENT_BLOCK_END}"""
_STDD_AGENT_BLOCK_PATTERN = re.compile(
    rf"{re.escape(STDD_AGENT_BLOCK_START)}.*?{re.escape(STDD_AGENT_BLOCK_END)}\n?",
    re.DOTALL,
)


def ensure_agent_instructions(root: Path, integrations: tuple[str, ...]) -> list[Path]:
    """Instala instruções locais do STDD nos arquivos reconhecidos por cada agente.
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
        without_stdd = _STDD_AGENT_BLOCK_PATTERN.sub("", existing).lstrip("\n")
        updated = STDD_AGENT_BLOCK + ("\n\n" + without_stdd if without_stdd else "\n")
        if updated != existing:
            instruction_path.parent.mkdir(parents=True, exist_ok=True)
            instruction_path.write_text(updated, encoding="utf-8")
            changed.append(instruction_path)
    return changed


def init_project(root: Path, integrations: tuple[str, ...] = ("codex",)) -> list[Path]:
    """Inicializa a estrutura do projeto e instala as skills dos agentes.
    Cria as pastas internas de execuções/features e copia os templates Markdown para .agents/skills.
    """
    created: list[Path] = []
    for directory in (
        stdd_dir(root) / "runs",
        stdd_dir(root) / "features",
        *(root / AGENT_SKILL_DIRECTORIES[integration] for integration in integrations),
    ):
        if not directory.exists():
            directory.mkdir(parents=True)
            created.append(directory)

    config = stdd_dir(root) / "config.json"
    if not config.exists():
        config.write_text(
            json.dumps(
                {
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
                    "version": 1,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        created.append(config)

    created.extend(ensure_static_analysis_defaults(config))

    created.extend(ensure_draw_workspace(root, include_example=True))
    created.extend(ensure_improvement_workspace(root))
    created.extend(ensure_runs_workspace(root))
    created.extend(ensure_gitignore(root))

    for integration in integrations:
        for source in agent_templates():
            name = source.parent.name
            sources = [source]
            openai_metadata = source.parent / "agents" / "openai.yaml"
            if integration == "codex" and openai_metadata.exists():
                sources.append(openai_metadata)
            for skill_source in sources:
                relative = skill_source.relative_to(source.parent)
                target = root / AGENT_SKILL_DIRECTORIES[integration] / name / relative
                source_text = skill_source.read_text(encoding="utf-8")
                if not target.exists() or target.read_text(encoding="utf-8") != source_text:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(source_text, encoding="utf-8")
                    if target not in created:
                        created.append(target)
    created.extend(ensure_agent_instructions(root, integrations))
    return created


def ensure_static_analysis_defaults(config_path: Path) -> list[Path]:
    """Completa configurações antigas sem substituir escolhas existentes."""
    try:
        config_data = json.loads(config_path.read_text(encoding="utf-8"))
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
        config_path.write_text(json.dumps(config_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
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

    config_path = stdd_dir(root) / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
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


def get_workspace_snapshot(root: Path) -> dict[str, list[str]]:
    """Mapeia os arquivos rastreados da codebase e seus conteúdos em linhas.
    Filtra extensões configuradas e exclui o estado operacional do STDD.
    """
    tracked_exts = get_tracked_extensions(root)
    ignored_dirs = {".git", ".venv", "venv", "node_modules", *INTERNAL_STATE_DIRECTORIES, ".pytest_cache", "__pycache__"}
    
    gitignore_patterns = _parse_gitignore_dirs(root)
    for pattern in gitignore_patterns:
        if pattern.endswith("/"):
            ignored_dirs.add(pattern[:-1].split("/")[-1])
            
    import fnmatch

    snapshot: dict[str, list[str]] = {}
    for path in sorted(root.rglob("*")):
        ignored_by_file = False
        for pattern in gitignore_patterns:
            if not pattern.endswith("/") and fnmatch.fnmatch(path.name, pattern):
                ignored_by_file = True
                break

        if (
            path.is_file()
            and not ignored_by_file
            and path.suffix.lower() in tracked_exts
            and not ignored_dirs.intersection(path.parts)
        ):
            try:
                rel_path = str(path.relative_to(root))
                snapshot[rel_path] = path.read_text(encoding="utf-8").splitlines()
            except (UnicodeDecodeError, PermissionError):
                continue
    return snapshot


def get_draw_snapshot(root: Path) -> dict[str, list[str]]:
    """Mapeia somente os JSONs lógicos dos desenhos para o histórico de logs.
    Exclui o índice operacional e arquivos fora da pasta direta de Draws.
    """
    draws_dir = stdd_dir(root) / "draws"
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
    previous_snapshot = get_previous_workspace_snapshot(root)

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
    candidates = sorted((stdd_dir(root) / "runs").glob("*/*_snapshot.json"))
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
    candidates = sorted((stdd_dir(root) / "runs").glob("*/*_snapshot.json"))
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
    candidates = sorted((stdd_dir(root) / "runs").glob("*/*_snapshot.json"))
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
    """Cria o resumo e o snapshot detalhado do código na pasta .stdd/runs/YYYY-MM-DD/.
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
    runs_dir = stdd_dir(root) / "runs"
    summary_file = entry.write(runs_dir)
    update_runs_index(root, summary_file)
    return summary_file
