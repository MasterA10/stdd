"""Contratos e execução segura de adaptadores de análise estática.
Define o protocolo JSON agnóstico de linguagem usado pelo comando `stdd test`.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any


STATIC_ANALYSIS_CONTRACT_VERSION = "1"
ANALYSIS_COLLECTIONS = (
    "symbols",
    "dependencies",
    "complexity",
    "structural_metrics",
    "quality_findings",
    "changes",
)
REQUIRED_RESULT_FIELDS = (
    "contract_version",
    "status",
    "capabilities",
    *ANALYSIS_COLLECTIONS,
    "warnings",
    "errors",
)
VALID_STATUSES = {"passed", "unavailable", "blocked"}
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)(?<![A-Za-z0-9_])(?:[A-Za-z0-9]+_)?"
    r"(password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|private[_-]?key)"
    r"(?=\s*[:=])"
    r"\s*[:=]\s*(?P<quote>['\"])(?P<value>[^'\"\n]+)(?P=quote)"
)
SECRET_TOKEN_PATTERNS = (
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "aws_access_key"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"), "github_token"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "provider_api_key"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private_key"),
)
SECRET_SCAN_EXTENSIONS = {
    ".c", ".cc", ".cpp", ".cs", ".go", ".h", ".hpp", ".java", ".js", ".jsx", ".json",
    ".kt", ".php", ".py", ".rb", ".rs", ".sh", ".sql", ".swift", ".ts", ".tsx", ".toml",
    ".ini", ".cfg", ".conf", ".xml", ".yaml", ".yml",
}
SECRET_PLACEHOLDERS = {"test", "testing", "example", "dummy", "placeholder", "changeme", "change-me"}


def unavailable_result(reason: str) -> dict[str, Any]:
    """Cria um resultado explícito para uma análise estática indisponível.
    Mantém as coleções vazias para diferenciar ausência de dados de uma análise executada.
    """
    return {
        "contract_version": STATIC_ANALYSIS_CONTRACT_VERSION,
        "status": "unavailable",
        "reason": reason,
        "capabilities": {},
        **{collection: [] for collection in ANALYSIS_COLLECTIONS},
        "warnings": [reason],
        "errors": [],
    }


def blocked_result(reason: str, errors: list[str] | None = None) -> dict[str, Any]:
    """Cria um resultado bloqueado para falhas do contrato ou do adaptador.
    Preserva o motivo e as mensagens acionáveis sem copiar stdout ou stderr potencialmente sensíveis.
    """
    return {
        "contract_version": STATIC_ANALYSIS_CONTRACT_VERSION,
        "status": "blocked",
        "reason": reason,
        "capabilities": {},
        **{collection: [] for collection in ANALYSIS_COLLECTIONS},
        "warnings": [],
        "errors": errors or [reason],
    }


def scan_hardcoded_secrets(root: Path, files: list[str] | None = None) -> list[dict[str, Any]]:
    """Detecta literais suspeitos sem retornar o valor sensível.
    Analisa somente arquivos textuais de código/configuração fora de ambientes e artefatos ignorados.
    """
    ignored_parts = {".git", ".stdd", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}
    if files is None:
        candidates = sorted(
            path for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in SECRET_SCAN_EXTENSIONS
        )
    else:
        candidates = [root / relative for relative in files]
    findings: list[dict[str, Any]] = []
    env_values = _read_environment_values(root)
    code_contents: dict[str, str] = {}
    for path in candidates:
        if ignored_parts.intersection(path.parts) or path.name == ".env" or path.name.startswith(".env."):
            continue
        if path.suffix.lower() not in SECRET_SCAN_EXTENSIONS or not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
            relative = str(path.relative_to(root))
        except (OSError, UnicodeDecodeError, ValueError):
            continue
        code_contents[relative] = "\n".join(lines)
        for line_number, line in enumerate(lines, start=1):
            assignment = SECRET_ASSIGNMENT_PATTERN.search(line)
            if assignment:
                value = assignment.group("value").strip()
                normalized = value.lower()
                if value and normalized not in SECRET_PLACEHOLDERS and not value.startswith(("${", "<")):
                    findings.append(
                        {
                            "kind": "hardcoded_secret",
                            "severity": "blocking",
                            "file": relative,
                            "line": line_number,
                            "value": "[REDACTED]",
                            "evidence": f"literal assigned to {assignment.group(1).lower()}-like identifier",
                            "source": "builtin_secret_scanner",
                        }
                    )
                    continue
            for pattern, token_kind in SECRET_TOKEN_PATTERNS:
                if pattern.search(line):
                    findings.append(
                        {
                            "kind": "hardcoded_secret",
                            "severity": "blocking",
                            "file": relative,
                            "line": line_number,
                            "value": "[REDACTED]",
                            "evidence": f"literal matches {token_kind} pattern",
                            "source": "builtin_secret_scanner",
                        }
                    )
                    break
    for env_key, env_value, env_file in env_values:
        if not env_value or _is_safe_environment_value(env_value):
            continue
        references = [relative for relative, content in code_contents.items() if env_value in content]
        if references:
            for relative in references:
                line_number = next(
                    (index for index, line in enumerate(code_contents[relative].splitlines(), start=1) if env_value in line),
                    1,
                )
                findings.append(
                    {
                        "kind": "hardcoded_env_value",
                        "severity": "blocking",
                        "file": relative,
                        "line": line_number,
                        "env_key": env_key,
                        "value": "[REDACTED]",
                        "evidence": f"value from {env_file} is present in source code",
                        "source": "builtin_secret_scanner",
                    }
                )
        elif not any(re.search(rf"(?<![A-Za-z0-9_]){re.escape(env_key)}(?![A-Za-z0-9_])", content) for content in code_contents.values()):
            findings.append(
                {
                    "kind": "unreferenced_env_variable",
                    "severity": "warning",
                    "file": env_file,
                    "env_key": env_key,
                    "value": "[REDACTED]",
                    "evidence": "environment variable has no code reference",
                    "source": "builtin_secret_scanner",
                }
            )
    return findings


def _read_environment_values(root: Path) -> list[tuple[str, str, str]]:
    """Lê nomes e valores de arquivos `.env` sem expor o conteúdo no relatório.
    Aceita arquivos de ambiente locais e devolve apenas dados internos para comparação.
    """
    values: list[tuple[str, str, str]] = []
    for path in sorted(root.glob(".env*")):
        if not path.is_file() or path.name == ".env.example":
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line in lines:
            match = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$", line)
            if not match:
                continue
            value = match.group(2).strip().strip("'\"")
            values.append((match.group(1), value, path.name))
    return values


def _is_safe_environment_value(value: str) -> bool:
    """Indica se um valor de ambiente é vazio, placeholder ou curto demais para comparar.
    Evita avisos pouco confiáveis para exemplos e valores booleanos ou numéricos comuns.
    """
    return not value or len(value) < 8 or value.lower() in SECRET_PLACEHOLDERS or value.startswith(("${", "<"))


def validate_static_analysis_result(result: Any) -> list[str]:
    """Valida a forma mínima do relatório produzido por um adaptador.
    Rejeita versões, status, coleções e tipos incompatíveis antes da aprovação.
    """
    if not isinstance(result, dict):
        return ["resultado da análise estática deve ser um objeto JSON"]

    violations: list[str] = []
    missing = [field for field in REQUIRED_RESULT_FIELDS if field not in result]
    if missing:
        violations.append(f"campos obrigatórios ausentes: {', '.join(missing)}")
    if result.get("contract_version") != STATIC_ANALYSIS_CONTRACT_VERSION:
        violations.append("versão do contrato de análise estática incompatível")
    if result.get("status") not in VALID_STATUSES:
        violations.append("status da análise estática inválido")
    if not isinstance(result.get("capabilities"), dict):
        violations.append("capabilities deve ser um objeto")

    for collection in (*ANALYSIS_COLLECTIONS, "warnings", "errors"):
        value = result.get(collection)
        if not isinstance(value, list):
            violations.append(f"{collection} deve ser uma lista")
        elif any(not isinstance(item, dict) and collection not in {"warnings", "errors"} for item in value):
            violations.append(f"itens de {collection} devem ser objetos")
        elif any(not isinstance(item, str) for item in value) and collection in {"warnings", "errors"}:
            violations.append(f"itens de {collection} devem ser textos")
    return violations


def build_analysis_request(root: Path, execution_id: str, changed_files: list[str]) -> dict[str, Any]:
    """Monta a requisição versionada enviada ao adaptador externo.
    Inclui somente caminhos relativos, modo incremental e o identificador da execução.
    """
    return {
        "contract_version": STATIC_ANALYSIS_CONTRACT_VERSION,
        "execution_id": execution_id,
        "project_path": str(root),
        "changed_files": sorted(changed_files),
        "mode": "incremental" if changed_files else "full",
    }


def run_static_analysis(
    root: Path,
    execution_id: str,
    config: dict[str, Any],
    changed_files: list[str],
) -> dict[str, Any]:
    """Executa o adaptador configurado e valida seu relatório JSON.
    Não usa shell, não expõe stderr e bloqueia configurações ou respostas inválidas.
    """
    static_config = config.get("static_analysis", {})
    if static_config is None:
        static_config = {}
    if not isinstance(static_config, dict):
        return blocked_result("static_analysis_config_invalid", ["static_analysis deve ser um objeto"])
    if static_config.get("enabled", True) is False:
        return unavailable_result("static_analysis_disabled")

    builtin_findings = scan_hardcoded_secrets(root, changed_files)

    command = static_config.get("adapter_command")
    if command is None:
        result = unavailable_result("adapter_not_configured")
        result["capabilities"] = {"secrets": True}
        result["quality_findings"] = builtin_findings
        blocking_findings = [finding for finding in builtin_findings if finding.get("severity") == "blocking"]
        if blocking_findings:
            result["status"] = "blocked"
            result["reason"] = "hardcoded_secret"
            result["errors"] = [f"{len(blocking_findings)} segredo(s) hardcoded detectado(s)"]
        return result
    if (
        not isinstance(command, list)
        or not command
        or any(not isinstance(argument, str) or not argument for argument in command)
    ):
        return blocked_result("adapter_command_invalid", ["adapter_command deve ser uma lista de argumentos não vazios"])

    request = build_analysis_request(root, execution_id, changed_files)
    try:
        process = subprocess.run(
            command,
            cwd=root,
            input=json.dumps(request, ensure_ascii=False),
            text=True,
            capture_output=True,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return blocked_result("adapter_execution_failed", [f"não foi possível executar o adaptador: {error.__class__.__name__}"])

    if process.returncode != 0:
        return blocked_result("adapter_exit_code", [f"o adaptador terminou com exit code {process.returncode}"])
    try:
        result = json.loads(process.stdout)
    except json.JSONDecodeError:
        return blocked_result("adapter_output_invalid", ["a saída do adaptador não é JSON válido"])

    violations = validate_static_analysis_result(result)
    if violations:
        return blocked_result("adapter_schema_invalid", violations)
    result["quality_findings"] = [*result["quality_findings"], *builtin_findings]
    blocking_findings = [
        finding
        for finding in result["quality_findings"]
        if finding.get("severity") == "blocking"
    ]
    if blocking_findings and result["status"] == "passed":
        result["status"] = "blocked"
        result["reason"] = "quality_gate_blocked"
        result["errors"] = [
            *result["errors"],
            f"{len(blocking_findings)} achado(s) de qualidade bloqueante(s)",
        ]
    return result
