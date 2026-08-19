from __future__ import annotations

import ast
import json
from pathlib import Path


def contract_config(root: Path) -> dict:
    """Lê a configuração do contrato do projeto.
    Carrega o arquivo .looper/config.json e retorna a seção contract.
    """
    config_path = root / ".looper" / "config.json"
    if not config_path.exists():
        return {"enabled": True, "code_language": "python", "description_language": "pt-BR"}
    config = json.loads(config_path.read_text(encoding="utf-8"))
    return config.get("contract", {"enabled": True, "code_language": "python", "description_language": "pt-BR"})


def python_files(root: Path) -> list[Path]:
    """Localiza arquivos Python sujeitos ao contrato.
    Percorre a árvore de diretórios ignorando pastas ocultas e de ambiente.
    """
    ignored = {".git", ".venv", "venv", "node_modules", ".looper"}
    return sorted(
        path
        for path in root.rglob("*.py")
        if not ignored.intersection(path.parts)
    )


def check_python_function_descriptions(root: Path) -> list[str]:
    """Valida descrições de duas linhas nas funções de teste Python.
    Examina somente arquivos sob tests/ e deixa comentários de produção para decisões importantes.
    """
    violations: list[str] = []
    for path in python_files(root):
        relative_path = path.relative_to(root)
        if "tests" not in relative_path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            description = ast.get_docstring(node, clean=True)
            if not description or not description.strip():
                violations.append(f"{relative_path}:{node.lineno}: teste sem descrição curta")
                continue
            lines = [line.strip() for line in description.strip().splitlines() if line.strip()]
            if len(lines) < 2:
                violations.append(f"{relative_path}:{node.lineno}: teste deve ter 2 comentários/linhas (o que faz e como faz)")
                continue
            if len(lines) > 2 or any(len(line) > 160 for line in lines):
                violations.append(f"{relative_path}:{node.lineno}: descrição do teste deve ser curta")
    return violations


def check_contract(root: Path) -> list[str]:
    """Valida o contrato de documentação conforme a configuração do projeto.
    Verifica se o contrato está ativo e aciona os verificadores de linguagem.
    """
    config = contract_config(root)
    if not config.get("enabled", True):
        return []
    if config.get("code_language", "python") != "python":
        return []
    return check_python_function_descriptions(root)
