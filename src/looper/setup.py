"""Descoberta de stack e configuração específica do projeto.
O módulo mantém o núcleo independente da linguagem executada pela aplicação.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

from .config import load_config, save_config


SUPPORTED_INTEGRATIONS = ("codex",)
DESIGN_TEMPLATE = """<!doctype html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>Design system do projeto</title></head>
<body>
<h1>Design system do projeto</h1>
<p data-status="incomplete">[PREENCHER] Substitua este bloco pelas decisões visuais aprovadas.</p>

> [PREENCHER] Substitua este bloco pelas decisões visuais aprovadas do produto.

<h2>Identidade visual</h2>

<ul><li>Marca, tom e referências: [PREENCHER]</li>
<li>Tipografia e hierarquia: [PREENCHER]</li>
<li>Cores e estados: [PREENCHER]</li></ul>

<h2>Tokens do sistema</h2>

<ul><li>Cores semânticas (surface, text, border, action e feedback): [PREENCHER]</li>
<li>Tipografia (famílias, escala, pesos e line-height): [PREENCHER]</li>
<li>Espaçamento, grid, containers e breakpoints: [PREENCHER]</li>
<li>Raios, bordas, sombras e densidade: [PREENCHER]</li></ul>

<h2>Componentes e estados</h2>

<ul><li>Estados de loading, vazio, erro, sucesso, hover, ativo, desabilitado e foco: [PREENCHER]</li>
<li>Movimento e <code>prefers-reduced-motion</code>: [PREENCHER]</li>
<li>Acessibilidade e contraste mínimo: texto normal 4.5:1; texto grande 3:1; componentes 3:1.</li></ul>
</body></html>

## Integrações externas

- API/app/provedor e documentação oficial do contrato: [PREENCHER]
"""


def ensure_design_document(root: Path) -> Path:
    """Cria o documento de design versionável sem fingir decisões do produto."""
    path = root / ".looper" / "design.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(DESIGN_TEMPLATE, encoding="utf-8")
    return path


def bootstrap_design_status(root: Path) -> dict[str, Any]:
    """Retorna a evidência do design sem aceitar template não preenchido."""
    path = root / ".looper" / "design.html"
    if not path.is_file():
        return {"status": "blocked", "reason": "design_missing", "file": ".looper/design.html"}
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return {"status": "blocked", "reason": "design_unreadable", "file": ".looper/design.html"}
    if not content.strip():
        return {"status": "blocked", "reason": "design_empty", "file": ".looper/design.html"}
    if "[PREENCHER]" in content:
        return {"status": "blocked", "reason": "design_template_unfilled", "file": ".looper/design.html"}
    return {"status": "passed", "file": ".looper/design.html"}
STACK_GITIGNORE_RULES = {
    "python": (".pytest_cache/", ".mypy_cache/", ".ruff_cache/"),
    "javascript": ("dist/",),
    "typescript": ("dist/",),
    "rust": ("target/",),
    "java": ("target/",),
    "csharp": ("bin/", "obj/"),
    "php": ("vendor/",),
}
def detect_stack(root: Path) -> dict[str, Any]:
    """Detecta linguagens, frameworks e runners por arquivos de configuração.
    Retorna somente evidências locais e não executa instalações ou comandos caros.
    """
    languages: list[str] = []
    frameworks: list[str] = []
    runners: list[str] = []
    test_command: list[str] | None = None

    package_files = _project_package_files(root)
    package_json = root / "package.json"
    for package_file in package_files:
        data = _read_json(package_file)
        dependencies = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        package_root = package_file.parent
        languages.append("typescript" if (package_root / "tsconfig.json").exists() or any("typescript" in key for key in dependencies) or any(name in dependencies for name in ("vitest", "ts-jest", "tsx")) else "javascript")
        frameworks.extend(_matching_names(dependencies, ("react", "next", "vue", "angular", "express", "fastify", "nestjs")))
        script = data.get("scripts", {}).get("test") if isinstance(data.get("scripts"), dict) else None
        if package_file != package_json:
            runners.append(f"{package_file.parent.relative_to(root).as_posix()}:javascript")
        if isinstance(script, str) and script.strip():
            runners.append(script.split()[0])
            if package_file == package_json:
                test_command = ["npm", "test"] if (root / "package-lock.json").exists() else _package_manager_command(root, "test")

    if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists() or (root / "setup.py").exists():
        languages.append("python")
        content = _read_text(root / "pyproject.toml") + _read_text(root / "requirements.txt")
        frameworks.extend(_matching_text(content, ("fastapi", "django", "flask", "sqlalchemy")))
        if "pytest" in content or (root / "tests").exists():
            runners.append("pytest")
            test_command = ["python", "-m", "pytest"]

    # O pacote do Looper distribui templates de adapters PHP para outros projetos.
    # Esses templates não são evidência da linguagem da aplicação atual.
    php_files = _project_php_files(root)
    composer = root / "composer.json"
    if composer.exists() or php_files:
        languages.append("php")
        composer_data = _read_json(composer) if composer.exists() else {}
        dependencies = {
            **(composer_data.get("require", {}) if isinstance(composer_data.get("require"), dict) else {}),
            **(composer_data.get("require-dev", {}) if isinstance(composer_data.get("require-dev"), dict) else {}),
        }
        frameworks.extend(_matching_names(dependencies, ("wordpress", "laravel", "symfony", "slim", "laminas")))
        scripts = composer_data.get("scripts", {})
        composer_test = scripts.get("test") if isinstance(scripts, dict) else None
        if isinstance(composer_test, str) and composer_test.strip():
            runners.append("composer")
            test_command = ["composer", "test"]
        elif (root / "phpunit.xml").exists() or (root / "phpunit.xml.dist").exists():
            runners.append("phpunit")
            phpunit = root / "vendor/bin/phpunit"
            test_command = [str(phpunit), "--configuration", "phpunit.xml"] if phpunit.exists() else ["phpunit"]
        else:
            custom_runner = _find_php_test_runner(root)
            if custom_runner:
                runners.append("php custom runner")
                test_command = ["php", custom_runner]
        if "wordpress" in dependencies or _looks_like_wordpress(root, php_files):
            if "wordpress" not in frameworks:
                frameworks.append("wordpress")

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
    config = load_config(root)
    stack = detect_stack(root)
    config["stack"] = {key: value for key, value in stack.items() if key != "test_command"}
    if stack["test_command"] and not config.get("test_commands"):
        config["test_commands"] = [{"name": "all", "command": stack["test_command"]}]
    analyzable = {"python", "javascript", "typescript", "php"}.intersection(stack["languages"])
    if analyzable:
        static_config = config.setdefault("static_analysis", {})
        current_command = static_config.get("adapter_command") if isinstance(static_config, dict) else None
        legacy_php = analyzable == {"php"} and isinstance(current_command, list) and current_command == ["php", ".looper/adapters/php_static_adapter.php"]
        replace_generated = isinstance(current_command, list) and any(str(item).endswith("python_static_adapter.py") for item in current_command)
        if isinstance(static_config, dict) and analyzable == {"php"} and not current_command and shutil.which("php"):
            adapter = ensure_php_adapter(root)
            if adapter:
                static_config["adapter_command"] = ["php", str(adapter.relative_to(root))]
        elif isinstance(static_config, dict) and (not current_command or replace_generated) and len(analyzable) > 1:
            adapter = ensure_static_adapter(root, stack["languages"])
            if adapter:
                static_config["adapter_command"] = [_python_executable(), str(adapter.relative_to(root))]
        elif isinstance(static_config, dict) and legacy_php and not (root / ".looper/adapters/php_static_adapter.php").exists():
            adapter = ensure_php_adapter(root)
            if adapter:
                static_config["adapter_command"] = ["php", str(adapter.relative_to(root))]
    save_config(root, config)
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
    candidates = ("package.json", "tsconfig.json", "pyproject.toml", "requirements.txt", "go.mod", "Cargo.toml", "pom.xml", "mvnw", "composer.json", "phpunit.xml", "phpunit.xml.dist")
    evidence = [name for name in candidates if (root / name).exists()]
    nested_packages = [path.relative_to(root).as_posix() for path in _project_package_files(root) if path != root / "package.json"]
    evidence.extend(nested_packages)
    if not evidence and _project_php_files(root):
        evidence.append("*.php")
    for runner in _php_runner_evidence(root):
        if runner not in evidence:
            evidence.append(runner)
    return evidence


def _project_php_files(root: Path) -> list[Path]:
    """Lista PHP da aplicação, ignorando artefatos e templates internos do Looper."""
    ignored_parts = {".git", ".looper", "node_modules", "vendor", "__pycache__"}
    files: list[Path] = []
    for path in root.rglob("*.php"):
        relative = path.relative_to(root)
        if ignored_parts.intersection(relative.parts):
            continue
        if relative.parts[:3] == ("src", "looper", "templates"):
            continue
        files.append(path)
    return sorted(files)


def _find_php_test_runner(root: Path) -> str | None:
    """Encontra um runner PHP local sem executar código ou instalar dependências."""
    return next((path for path in _php_runner_evidence(root) if path.endswith(".php")), None)


def _php_runner_evidence(root: Path) -> list[str]:
    """Lista runners PHP convencionais com caminhos relativos estáveis."""
    candidates = sorted(
        path.relative_to(root).as_posix()
        for path in root.glob("tests/**/run.php")
        if path.is_file()
    )
    if (root / "test.php").is_file():
        candidates.append("test.php")
    return candidates


def _looks_like_wordpress(root: Path, php_files: list[Path]) -> bool:
    """Reconhece WordPress apenas por marcadores locais, sem carregar a aplicação."""
    for path in php_files[:200]:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")[:12000].lower()
        except OSError:
            continue
        if "wp-content/plugins" in str(root).lower() or "plugin name:" in content or "abspath" in content:
            return True
    return False


def ensure_php_adapter(root: Path) -> Path | None:
    """Materializa o adapter PHP nativo do Looper quando o CLI PHP está disponível."""
    if shutil.which("php") is None:
        return None
    source = Path(__file__).parent / "templates" / "adapters" / "php_static_adapter.php"
    if not source.exists():
        return None
    target = root / ".looper" / "adapters" / "php_static_adapter.php"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    return target


def _project_package_files(root: Path) -> list[Path]:
    """Encontra manifests JavaScript/TypeScript em um monorepo sem atravessar artefatos."""
    ignored = {".git", ".looper", "node_modules", "vendor", "dist", "build", "coverage"}
    return sorted(
        path for path in root.rglob("package.json")
        if path.is_file() and not ignored.intersection(path.relative_to(root).parts)
    )


def ensure_static_adapter(root: Path, languages: list[str]) -> Path | None:
    """Materializa o dispatcher e os módulos específicos das linguagens detectadas."""
    sources = Path(__file__).parent / "templates" / "adapters"
    target_dir = root / ".looper" / "adapters"
    target_dir.mkdir(parents=True, exist_ok=True)
    dispatcher = target_dir / "static_adapter.py"
    source = sources / "static_adapter.py"
    if not dispatcher.exists() and source.exists():
        dispatcher.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    if any(language in languages for language in ("javascript", "typescript")):
        js_source = sources / "js_ts_static_adapter.js"
        js_target = target_dir / js_source.name
        if not js_target.exists() and js_source.exists():
            js_target.write_text(js_source.read_text(encoding="utf-8"), encoding="utf-8")
    if "php" in languages:
        ensure_php_adapter(root)
    return dispatcher if dispatcher.exists() else None


def _python_executable() -> str:
    """Escolhe um executável Python portável para o comando do adapter."""
    return shutil.which("python") or shutil.which("python3") or sys.executable
