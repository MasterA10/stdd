"""Descoberta de stack e configuração específica do projeto.
O módulo mantém o núcleo independente da linguagem executada pela aplicação.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


SUPPORTED_INTEGRATIONS = ("codex", "claude", "gemini")
STACK_GITIGNORE_RULES = {
    "python": (".pytest_cache/", ".mypy_cache/", ".ruff_cache/"),
    "javascript": ("dist/",),
    "typescript": ("dist/",),
    "rust": ("target/",),
    "java": ("target/",),
    "csharp": ("bin/", "obj/"),
}


def detect_stack(root: Path) -> dict[str, Any]:
    """Detecta linguagens, frameworks e runners por arquivos de configuração.
    Retorna somente evidências locais e não executa instalações ou comandos caros.
    """
    languages: list[str] = []
    frameworks: list[str] = []
    runners: list[str] = []
    test_command: list[str] | None = None

    package_json = root / "package.json"
    if package_json.exists():
        data = _read_json(package_json)
        dependencies = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        languages.append("typescript" if (root / "tsconfig.json").exists() or any("typescript" in key for key in dependencies) or any(name in dependencies for name in ("vitest", "ts-jest", "tsx")) else "javascript")
        frameworks.extend(_matching_names(dependencies, ("react", "next", "vue", "angular", "express", "fastify", "nestjs")))
        script = data.get("scripts", {}).get("test") if isinstance(data.get("scripts"), dict) else None
        if isinstance(script, str) and script.strip():
            runners.append(script.split()[0])
            test_command = ["npm", "test"] if (root / "package-lock.json").exists() else _package_manager_command(root, "test")

    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists() or (root / "setup.py").exists():
        languages.append("python")
        content = _read_text(root / "pyproject.toml") + _read_text(root / "requirements.txt")
        frameworks.extend(_matching_text(content, ("fastapi", "django", "flask", "sqlalchemy")))
        if "pytest" in content or (root / "tests").exists():
            runners.append("pytest")
            test_command = ["python", "-m", "pytest"]

    if (root / "go.mod").exists():
        languages.append("go")
        runners.append("go test")
        test_command = ["go", "test", "./..."]
    if (root / "Cargo.toml").exists():
        languages.append("rust")
        runners.append("cargo test")
        test_command = ["cargo", "test"]
    if (root / "pom.xml").exists() or (root / "mvnw").exists():
        languages.append("java")
        runners.append("maven")
        test_command = ["./mvnw", "test"] if (root / "mvnw").exists() else ["mvn", "test"]
    if list(root.glob("*.csproj")) or list(root.glob("*.sln")):
        languages.append("csharp")
        runners.append("dotnet")
        test_command = ["dotnet", "test"]

    languages = list(dict.fromkeys(languages))
    frameworks = list(dict.fromkeys(frameworks))
    runners = list(dict.fromkeys(runners))
    return {
        "languages": languages,
        "frameworks": frameworks,
        "test_runners": runners,
        "evidence": _stack_evidence(root),
        "status": "detected" if languages else "unknown",
        "test_command": test_command,
    }


def configure_project(root: Path) -> dict[str, Any]:
    """Atualiza a configuração com a stack detectada e seu runner nativo.
    Mantém comandos previamente configurados e só adiciona um runner quando há evidência.
    """
    config_path = root / ".stdd" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    stack = detect_stack(root)
    config["stack"] = {key: value for key, value in stack.items() if key != "test_command"}
    if stack["test_command"] and not config.get("test_commands"):
        config["test_commands"] = [{"name": "all", "command": stack["test_command"]}]
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return stack


def ensure_stack_gitignore(root: Path, languages: list[str]) -> bool:
    """Adiciona padrões de artefatos da stack ao `.gitignore` sem apagar regras.
    Mantém a escrita idempotente para que o setup possa ser executado novamente com segurança.
    """
    path = root / ".gitignore"
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = existing.splitlines()
    rules = [rule for language in languages for rule in STACK_GITIGNORE_RULES.get(language, ())]
    missing = list(dict.fromkeys(rule for rule in rules if rule not in lines))
    if not missing:
        return False
    updated = existing
    if updated and not updated.endswith("\n"):
        updated += "\n"
    if updated and not updated.endswith("\n\n"):
        updated += "\n"
    path.write_text(updated + "\n".join(missing) + "\n", encoding="utf-8")
    return True


def available_integrations() -> dict[str, bool]:
    """Detecta agentes locais sem instalar ou iniciar nenhum executável.
    Retorna apenas disponibilidade observável no PATH para diagnóstico do setup.
    """
    return {name: shutil.which(name) is not None for name in SUPPORTED_INTEGRATIONS}


def _read_json(path: Path) -> dict[str, Any]:
    """Lê JSON de configuração ou devolve objeto vazio para conteúdo inválido.
    Mantém a descoberta diagnóstica tolerante a arquivos incompletos.
    """
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _read_text(path: Path) -> str:
    """Lê um arquivo textual opcional para procurar marcadores de stack.
    Arquivos ausentes ou ilegíveis não interrompem a inicialização.
    """
    try:
        return path.read_text(encoding="utf-8").lower()
    except (OSError, UnicodeDecodeError):
        return ""


def _matching_names(values: dict[str, Any], names: tuple[str, ...]) -> list[str]:
    """Seleciona nomes de frameworks presentes em dependências declaradas.
    Usa somente chaves do manifesto e não resolve dependências remotamente.
    """
    return [name for name in names if any(name in dependency.lower() for dependency in values)]


def _matching_text(content: str, names: tuple[str, ...]) -> list[str]:
    """Seleciona frameworks por marcadores textuais locais.
    Retorna nomes estáveis para o relatório de descoberta.
    """
    return [name for name in names if name in content]


def _package_manager_command(root: Path, action: str) -> list[str]:
    """Escolhe o gerenciador JavaScript indicado pelo lockfile existente.
    Não instala ferramentas e usa npm como fallback portável.
    """
    if (root / "pnpm-lock.yaml").exists():
        return ["pnpm", action]
    if (root / "yarn.lock").exists():
        return ["yarn", action]
    return ["npm", action]


def _stack_evidence(root: Path) -> list[str]:
    """Lista manifests locais que sustentam a detecção da stack.
    Os caminhos são relativos e não contêm valores de configuração.
    """
    candidates = ("package.json", "tsconfig.json", "pyproject.toml", "requirements.txt", "go.mod", "Cargo.toml", "pom.xml", "mvnw")
    return [name for name in candidates if (root / name).exists()]
