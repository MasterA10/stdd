from __future__ import annotations

from pathlib import Path
from typing import Any

from ..adapters.registry import detect_project
from ..agents.projections import install_projections
from ..config.project import create_profile
from ..git.hooks import install_hooks
from ..git.repository import GitRepository
from ..reporting.models import CommandResult


def _inside(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    if root not in path.parents and path != root:
        raise ValueError("requirements file must remain inside project root")
    return path


def _infer_requirements(root: Path, requirements: str | None) -> dict[str, str]:
    if not requirements:
        return {}
    path = _inside(root, requirements)
    if not path.is_file():
        raise FileNotFoundError(path)
    text = path.read_text(errors="replace").lower()
    values: dict[str, str] = {}
    language_map = (("typescript", "typescript"), ("javascript", "javascript"),
                    ("python", "python"), ("golang", "go"), ("rust", "rust"),
                    ("java", "java"), ("php", "php"))
    framework_map = (("fastapi", "fastapi"), ("django", "django"), ("react", "react"),
                     ("next.js", "next.js"), ("nextjs", "next.js"), ("laravel", "laravel"),
                     ("spring", "spring"), ("nestjs", "nestjs"))
    for token, value in language_map:
        if token in text:
            values.setdefault("language", value)
            break
    for token, value in framework_map:
        if token in text:
            values["framework"] = value
            break
    for token in ("postgresql", "postgres", "mysql", "mariadb", "mongodb", "redis", "sqlite"):
        if token in text:
            values["database"] = "postgresql" if token == "postgres" else token
            break
    for token, value in (("pytest", "pytest"), ("vitest", "vitest"), ("jest", "jest"),
                         ("phpunit", "phpunit"), ("junit", "junit")):
        if token in text:
            values["test_runner"] = value
            break
    return values


def _root_detection(detection: dict[str, Any]) -> dict[str, Any]:
    return detection.setdefault("applications", {}).setdefault("root", {"path": "."})


def _guided_answers(root: Path, detection: dict[str, Any], inferred: dict[str, str],
                    profile: str = "mvp") -> dict[str, str]:
    app = _root_detection(detection)
    defaults = {"language": inferred.get("language") or (app.get("languages") or ["python"])[0],
                "framework": inferred.get("framework") or (app.get("frameworks") or ["none"])[0],
                "database": inferred.get("database", "none"),
                "test_runner": inferred.get("test_runner", "pytest"),
                "profile": profile}
    prompts = (("language", "Linguagem principal"), ("framework", "Framework principal"),
               ("database", "Banco de dados"), ("test_runner", "Runner de testes"),
               ("profile", "Perfil (experiment/mvp/product)"))
    answers = dict(defaults)
    for key, label in prompts:
        value = input(f"{label} [{defaults[key]}]: ").strip()
        if value:
            answers[key] = value
    if answers["profile"] not in {"experiment", "mvp", "product"}:
        answers["profile"] = profile
    return answers


def _apply_answers(detection: dict[str, Any], answers: dict[str, str]) -> None:
    app = _root_detection(detection)
    app["languages"] = [answers["language"]]
    app["frameworks"] = [] if answers["framework"] == "none" else [answers["framework"]]
    app["tests"] = {"runner": answers["test_runner"]}
    app["datastores"] = [] if answers["database"] == "none" else [answers["database"]]


def _confirm() -> bool:
    return input("Salvar esta configuração? [S/n]: ").strip().lower() not in {"n", "nao", "não", "no"}


def _initialize_framework_layout(root: Path) -> dict[str, Any]:
    directories = ("adapters", "scripts", "agents/requests", "agents/results", "security",
                   "quality", "cache", "generated", "history")
    for relative in directories:
        (root / ".framework" / relative).mkdir(parents=True, exist_ok=True)
    from ..index.symbols import update_symbol_index
    return {"directories": [f".framework/{item}" for item in directories],
            "indexed_symbols": update_symbol_index(root)}


def _prepare_options(result: CommandResult, root: Path, mode: str, detection: dict[str, Any],
                     inferred: dict[str, str], *, integration: str | None,
                     interactive: bool, profile: str) -> tuple[str, str | None] | None:
    if interactive and mode == "greenfield":
        answers = _guided_answers(root, detection, inferred, profile)
        _apply_answers(detection, answers)
        profile = answers["profile"]
        result.metadata["guided_answers"] = answers
        integration = integration or input("Integração local [codex/claude] [codex]: ").strip().lower() or "codex"
        if not _confirm():
            result.status = "cancelled"
            result.actions.append("Configuration was not saved")
            return None
    elif inferred:
        _apply_answers(detection, {"language": inferred.get("language", "python"),
                                   "framework": inferred.get("framework", "none"),
                                   "database": inferred.get("database", "none"),
                                   "test_runner": inferred.get("test_runner", "pytest")})
    if interactive and integration is None:
        integration = input("Integração local [codex/claude] [codex]: ").strip().lower() or "codex"
    return profile, integration


def _validate_integration(result: CommandResult, integration: str | None, interactive: bool) -> bool:
    if not interactive and integration is None:
        result.status, result.exit_code = "error", 2
        result.actions.append("Choose an integration with --integration codex or --integration claude")
        return False
    if integration not in {None, "codex", "claude"}:
        result.status, result.exit_code = "error", 2
        result.actions.append("Integration must be codex or claude")
        return False
    return True


def init_project(root: Path, *, integration: str | None = None, interactive: bool = False,
                 install_git_hooks: bool = False, requirements: str | None = None,
                 profile: str = "mvp") -> CommandResult:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    existing = [item for item in root.iterdir() if item.name != Path(requirements).name] if requirements else list(root.iterdir())
    mode = "greenfield" if not existing else "brownfield"
    detection = detect_project(root)
    result = CommandResult("framework init", project={"root": str(root), "detections": detection}, metadata={})
    try:
        inferred = _infer_requirements(root, requirements)
    except (FileNotFoundError, ValueError) as exc:
        result.status, result.exit_code = "error", 2
        result.actions.append(str(exc))
        return result
    options = _prepare_options(result, root, mode, detection, inferred,
                               integration=integration, interactive=interactive, profile=profile)
    if options is None:
        return result
    profile, integration = options
    if not _validate_integration(result, integration, interactive):
        return result
    config = create_profile(root, detection, profile=profile, integration=integration, mode=mode)
    result.project.update(config.to_dict())
    result.actions.append("Created .framework/project.yml")
    result.metadata["framework_layout"] = _initialize_framework_layout(root)
    if integration:
        projection = install_projections(root, [integration])
        result.metadata["projections"] = projection
        if projection["conflicts"]:
            result.status, result.exit_code = "error", 4
            result.actions.append("Resolve locally modified projections before reinstalling")
    git = GitRepository(root)
    if git.available:
        result.metadata["git"] = git.snapshot()
        if install_git_hooks:
            result.metadata["hooks"] = install_hooks(root)
    else:
        result.status = "degraded"
        result.metadata["degraded"] = ["history", "diff", "commit protection", "full secret scan"]
    return result
