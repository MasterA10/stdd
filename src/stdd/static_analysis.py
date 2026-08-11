"""Contratos e execução segura de adaptadores de análise estática.
Define o protocolo JSON agnóstico de linguagem usado pelo comando `stdd test`.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import date, datetime, timezone
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
STATIC_ANALYSIS_KPI_VERSION = 1
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
TEST_FIXTURE_MARKERS = {"test", "fixture", "mock", "fake", "dummy", "example", "placeholder", "invalid"}
TEST_CREDENTIAL_ALLOW_MARKER = "stdd:allow-credential"
FRONTEND_RULE_PREFIX = "frontend."
FRONTEND_PROTECTED_KINDS = {"hardcoded_secret", "hardcoded_env_value"}
FRONTEND_RULES = {
    "missing_destination",
    "dead_reference",
    "interactive_without_action",
    "decorative_semantics",
}
EXCEPTION_ACTIONS = {"warning", "ignore"}


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
        "applied_exceptions": [],
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
        "applied_exceptions": [],
    }


def scan_hardcoded_secrets(
    root: Path,
    files: list[str] | None = None,
    allow_marked_test_credentials: bool = True,
) -> list[dict[str, Any]]:
    """Detecta literais suspeitos sem retornar o valor sensível.
    Analisa somente arquivos textuais de código/configuração fora de ambientes e artefatos ignorados.
    """
    candidates = _secret_scan_candidates(root, files)
    findings: list[dict[str, Any]] = []
    code_contents: dict[str, str] = {}
    for path in candidates:
        source = _read_secret_source(root, path)
        if source is None:
            continue
        relative, lines = source
        code_contents[relative] = "\n".join(lines)
        findings.extend(_scan_secret_lines(relative, lines, allow_marked_test_credentials))
    findings.extend(_scan_environment_values(root, code_contents, allow_marked_test_credentials))
    return findings


def _secret_scan_candidates(root: Path, files: list[str] | None) -> list[Path]:
    """Resolve os arquivos candidatos sem atravessar artefatos ignorados."""
    if files is not None:
        return [root / relative for relative in files]
    ignored_parts = {".git", ".stdd", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}
    return sorted(
        path for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in SECRET_SCAN_EXTENSIONS and not ignored_parts.intersection(path.parts)
    )


def _read_secret_source(root: Path, path: Path) -> tuple[str, list[str]] | None:
    """Lê uma fonte textual elegível para o scanner."""
    if path.name == ".env" or path.name.startswith(".env.") or path.suffix.lower() not in SECRET_SCAN_EXTENSIONS or not path.is_file():
        return None
    try:
        return str(path.relative_to(root)), path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError, ValueError):
        return None


def _scan_secret_lines(relative: str, lines: list[str], allow_marked: bool) -> list[dict[str, Any]]:
    """Detecta atribuições e tokens suspeitos em uma fonte."""
    findings: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        assignment = SECRET_ASSIGNMENT_PATTERN.search(line)
        if assignment and _is_suspicious_assignment(relative, assignment):
            allowed = allow_marked and _is_marked_test_credential(relative, lines, line_number)
            findings.append(_credential_finding(
                "literal assigned to " + assignment.group(1).lower() + "-like identifier",
                relative,
                line_number,
                allowed,
            ))
            continue
        for pattern, token_kind in SECRET_TOKEN_PATTERNS:
            if pattern.search(line):
                allowed = allow_marked and _is_marked_test_credential(relative, lines, line_number)
                findings.append(_credential_finding(
                    "literal matches " + token_kind + " pattern",
                    relative,
                    line_number,
                    allowed,
                ))
                break
    return findings


def _is_suspicious_assignment(relative: str, assignment: re.Match[str]) -> bool:
    """Filtra placeholders, leituras indiretas e fixtures sintéticas já conhecidas."""
    value = assignment.group("value").strip()
    normalized = value.lower()
    return bool(
        value
        and normalized not in SECRET_PLACEHOLDERS
        and not value.startswith(("${", "<"))
        and not _is_obvious_test_fixture(relative, assignment, normalized)
    )


def _credential_finding(evidence: str, relative: str, line_number: int, allowed: bool) -> dict[str, Any]:
    """Monta um finding redigido, distinguindo exceção explícita de bloqueio."""
    finding = {
        "kind": "hardcoded_secret",
        "severity": "warning" if allowed else "blocking",
        "file": relative,
        "line": line_number,
        "value": "[REDACTED]",
        "evidence": evidence,
        "source": "builtin_secret_scanner",
    }
    if allowed:
        finding["exception"] = "explicit_test_credential_allowlist"
    return finding


def _scan_environment_values(root: Path, code_contents: dict[str, str], allow_marked: bool) -> list[dict[str, Any]]:
    """Compara valores de ambientes locais com fontes e preserva a redação."""
    findings: list[dict[str, Any]] = []
    for env_key, env_value, env_file in _read_environment_values(root):
        if not env_value or _is_safe_environment_value(env_value):
            continue
        references = [relative for relative, content in code_contents.items() if env_value in content]
        if references:
            for relative in references:
                line_number = next(
                    (index for index, line in enumerate(code_contents[relative].splitlines(), start=1) if env_value in line),
                    1,
                )
                allowed = allow_marked and _is_marked_test_credential(
                    relative,
                    code_contents[relative].splitlines(),
                    line_number,
                )
                findings.append(
                    {
                        "kind": "hardcoded_env_value",
                        "severity": "warning" if allowed else "blocking",
                        "file": relative,
                        "line": line_number,
                        "env_key": env_key,
                        "value": "[REDACTED]",
                        "evidence": f"value from {env_file} is present in source code",
                        "source": "builtin_secret_scanner",
                        **({"exception": "explicit_test_credential_allowlist"} if allowed else {}),
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


def _is_marked_test_credential(relative: str, lines: list[str], line_number: int) -> bool:
    """Permite conscientemente uma credencial fictícia somente dentro de um teste.
    A marca deve estar na própria linha ou na linha imediatamente anterior; o valor
    nunca é retornado e a ocorrência continua visível como warning.
    """
    path = Path(relative)
    parts = {part.lower() for part in path.parts}
    is_test_file = bool(parts.intersection({"test", "tests", "spec", "specs", "fixtures"})) or "test" in path.stem.lower()
    if not is_test_file or not 1 <= line_number <= len(lines):
        return False
    marker = TEST_CREDENTIAL_ALLOW_MARKER
    current = lines[line_number - 1].lower()
    previous = lines[line_number - 2].lower() if line_number > 1 else ""
    return marker in current or marker in previous


def _is_obvious_test_fixture(relative: str, assignment: re.Match[str], normalized: str) -> bool:
    """Ignora valores claramente sintéticos usados por testes de contrato.
    Variáveis de produção continuam bloqueadas; somente fixtures em arquivos de teste são filtradas.
    """
    path = Path(relative)
    parts = {part.lower() for part in path.parts}
    is_test_file = bool(parts.intersection({"test", "tests", "spec", "specs", "fixtures"})) or "test" in path.stem.lower()
    if not is_test_file:
        return False
    identifier = assignment.group(0).split("=", 1)[0].split(":", 1)[0].strip().lower()
    local_secret_name = identifier.lstrip("$") in {"secret", "token", "password", "api_key", "access_token"}
    return local_secret_name and (
        any(marker in normalized for marker in TEST_FIXTURE_MARKERS)
        or "secret" in normalized
        or "token" in normalized
    )


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


def validate_static_analysis_policy(static_config: dict[str, Any]) -> list[str]:
    """Valida as políticas locais que o núcleo aplica aos achados do adapter."""
    return [
        *_validate_frontend_policy(static_config.get("frontend", {})),
        *_validate_exceptions(static_config.get("exceptions", [])),
    ]


def _validate_frontend_policy(frontend: Any) -> list[str]:
    """Valida o interruptor e as regras específicas da superfície frontend."""
    violations: list[str] = []
    if frontend is None:
        frontend = {}
    if not isinstance(frontend, dict):
        violations.append("static_analysis.frontend deve ser um objeto")
    else:
        if not isinstance(frontend.get("enabled", False), bool):
            violations.append("static_analysis.frontend.enabled deve ser booleano")
        if frontend.get("mode", "blocking") not in {"blocking", "warning"}:
            violations.append("static_analysis.frontend.mode deve ser blocking ou warning")
        rules = frontend.get("rules", {})
        if not isinstance(rules, dict) or any(not isinstance(value, bool) for value in rules.values()):
            violations.append("static_analysis.frontend.rules deve ser um objeto de valores booleanos")

    return violations


def _validate_exceptions(exceptions: Any) -> list[str]:
    """Valida a lista de exceções sem aceitar alvos ambíguos."""
    violations: list[str] = []
    if not isinstance(exceptions, list):
        violations.append("static_analysis.exceptions deve ser uma lista")
        return violations
    for index, exception in enumerate(exceptions):
        violations.extend(_validate_exception(exception, index))
    return violations


def _validate_exception(exception: Any, index: int) -> list[str]:
    """Valida uma exceção e exige regra, alvo, motivo e expiração."""
    prefix = f"static_analysis.exceptions[{index}]"
    if not isinstance(exception, dict):
        return [f"{prefix} deve ser um objeto"]
    return [
        *_validate_exception_metadata(exception, prefix),
        *_validate_exception_target(exception, prefix),
    ]


def _validate_exception_metadata(exception: dict[str, Any], prefix: str) -> list[str]:
    """Valida regra, ação, justificativa e validade da exceção."""
    violations: list[str] = []
    if not isinstance(exception.get("rule"), str) or not exception["rule"].strip():
        violations.append(f"{prefix}.rule deve ser um texto não vazio")
    if exception.get("action") not in EXCEPTION_ACTIONS:
        violations.append(f"{prefix}.action deve ser warning ou ignore")
    if not isinstance(exception.get("reason"), str) or not exception["reason"].strip():
        violations.append(f"{prefix}.reason deve ser um texto não vazio")
    if not isinstance(exception.get("expires"), str):
        violations.append(f"{prefix}.expires deve ser uma data ISO")
    else:
        try:
            date.fromisoformat(exception["expires"])
        except ValueError:
            violations.append(f"{prefix}.expires deve ser uma data ISO válida")
    return violations


def _validate_exception_target(exception: dict[str, Any], prefix: str) -> list[str]:
    """Valida o único alvo permitido para uma exceção."""
    violations: list[str] = []
    scopes = [key for key in ("file", "symbol_id", "lines") if key in exception]
    if len(scopes) != 1:
        violations.append(f"{prefix} deve ter exatamente um alvo entre file, symbol_id ou lines")
    if "file" in exception:
        file_value = exception["file"]
        if (
            not isinstance(file_value, str)
            or not file_value.strip()
            or Path(file_value).is_absolute()
            or ".." in Path(file_value).parts
        ):
            violations.append(f"{prefix}.file deve ser um caminho relativo não vazio")
    if "symbol_id" in exception and (not isinstance(exception["symbol_id"], str) or not exception["symbol_id"].strip()):
        violations.append(f"{prefix}.symbol_id deve ser um texto não vazio")
    if "lines" in exception:
        lines = exception["lines"]
        if (
            not isinstance(lines, list)
            or len(lines) != 2
            or any(not isinstance(line, int) or line < 1 for line in lines)
            or lines[0] > lines[1]
        ):
            violations.append(f"{prefix}.lines deve conter duas linhas inteiras válidas")
    return violations


def _finding_rule(finding: dict[str, Any]) -> str:
    """Retorna a identidade estável usada para habilitar e excepcionar um finding."""
    value = finding.get("rule") or finding.get("kind") or "unknown"
    return str(value)


def _is_frontend_finding(finding: dict[str, Any]) -> bool:
    """Reconhece achados frontend sem exigir que adapters antigos conheçam domain."""
    return finding.get("domain") == "frontend" or _finding_rule(finding).startswith(FRONTEND_RULE_PREFIX)


def _frontend_rule_enabled(finding: dict[str, Any], frontend: dict[str, Any]) -> bool:
    """Aplica a chave curta ou completa da regra frontend."""
    rules = frontend.get("rules", {})
    rule = _finding_rule(finding)
    short_rule = rule.removeprefix(FRONTEND_RULE_PREFIX)
    return rules.get(rule, rules.get(short_rule, True)) is not False


def _finding_line(finding: dict[str, Any]) -> int | None:
    """Obtém a linha do finding em formatos aceitos pelo contrato."""
    if isinstance(finding.get("line"), int):
        return finding["line"]
    position = finding.get("position")
    if isinstance(position, dict):
        for key in ("line", "start_line"):
            if isinstance(position.get(key), int):
                return position[key]
    return None


def _exception_matches(exception: dict[str, Any], finding: dict[str, Any]) -> bool:
    """Confere regra e alvo de uma exceção sem usar curingas implícitos."""
    exception_rule = str(exception.get("rule", ""))
    finding_rule = _finding_rule(finding)
    if exception_rule not in {finding_rule, finding_rule.removeprefix(FRONTEND_RULE_PREFIX)}:
        return False
    if "file" in exception:
        return finding.get("file") == exception["file"]
    if "symbol_id" in exception:
        return finding.get("symbol_id") == exception["symbol_id"]
    line = _finding_line(finding)
    return line is not None and exception["lines"][0] <= line <= exception["lines"][1]


def _expired_exception_finding(exception: dict[str, Any], index: int) -> dict[str, Any] | None:
    """Transforma uma exceção vencida em finding bloqueante, sem ocultar o alvo."""
    if date.fromisoformat(exception["expires"]) >= date.today():
        return None
    target = exception.get("file") or exception.get("symbol_id") or str(exception.get("lines"))
    return {
        "kind": "static_analysis.exception_expired",
        "rule": "static_analysis.exception_expired",
        "severity": "blocking",
        "file": str(target),
        "value": 1,
        "limit": 0,
        "evidence": f"exception-{index + 1} expirou em {exception['expires']}",
        "source": "builtin_static_policy",
    }


def apply_static_analysis_policy(
    findings: list[dict[str, Any]],
    static_config: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Aplica frontend, exceções e expiração antes do quality gate.

    Exceções mantêm evidência em ``applied_exceptions`` e nunca se aplicam aos
    achados de segredo protegidos pelo scanner interno.
    """
    frontend = static_config.get("frontend", {})
    if not isinstance(frontend, dict):
        frontend = {}
    exceptions = static_config.get("exceptions", [])
    if not isinstance(exceptions, list):
        exceptions = []
    output: list[dict[str, Any]] = []
    applied: list[dict[str, Any]] = []

    for index, exception in enumerate(exceptions):
        expired = _expired_exception_finding(exception, index)
        if expired:
            output.append(expired)

    for original in findings:
        if not isinstance(original, dict):
            continue
        finding = dict(original)
        if _is_frontend_finding(finding):
            if frontend.get("enabled", False) is not True or not _frontend_rule_enabled(finding, frontend):
                continue
            if frontend.get("mode", "blocking") == "warning" and finding.get("severity") == "blocking":
                finding["severity"] = "warning"
                finding["policy"] = "frontend_warning_mode"

        matched = None
        if finding.get("kind") not in FRONTEND_PROTECTED_KINDS:
            matched = next(
                (exception for exception in exceptions if date.fromisoformat(exception["expires"]) >= date.today() and _exception_matches(exception, finding)),
                None,
            )
        if matched:
            exception_id = matched.get("id", f"exception-{exceptions.index(matched) + 1}")
            applied.append({
                "id": exception_id,
                "rule": matched["rule"],
                "action": matched["action"],
                "file": finding.get("file"),
                "symbol_id": finding.get("symbol_id"),
            })
            if matched["action"] == "ignore":
                continue
            finding["severity"] = "warning"
            finding["exception_applied"] = exception_id
        output.append(finding)
    return output, applied


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


def _apply_quality_gate(
    result: dict[str, Any],
    builtin_findings: list[dict[str, Any]],
    static_config: dict[str, Any],
) -> dict[str, Any]:
    """Combina findings, aplica políticas e bloqueia somente o que restou ativo."""
    result["quality_findings"], result["applied_exceptions"] = apply_static_analysis_policy(
        [*result.get("quality_findings", []), *builtin_findings],
        static_config,
    )
    blocking_findings = [
        finding for finding in result["quality_findings"]
        if finding.get("severity") == "blocking"
    ]
    if not blocking_findings:
        return result
    result["status"] = "blocked"
    if any(finding.get("kind") in FRONTEND_PROTECTED_KINDS for finding in blocking_findings):
        result["reason"] = "hardcoded_secret"
        message = f"{len(blocking_findings)} segredo(s) hardcoded detectado(s)"
    else:
        result["reason"] = "quality_gate_blocked"
        message = f"{len(blocking_findings)} achado(s) de qualidade bloqueante(s)"
    if message not in result["errors"]:
        result["errors"].append(message)
    return result


def _kpi_exception_counts(
    report: dict[str, Any],
    findings: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Resume exceções aplicadas e vencidas para o snapshot do viewer."""
    applied = [item for item in report.get("applied_exceptions", []) if isinstance(item, dict)]
    expired = sum(item.get("kind") == "static_analysis.exception_expired" for item in findings)
    return applied, expired


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

    policy_violations = validate_static_analysis_policy(static_config)
    if policy_violations:
        return blocked_result("static_analysis_config_invalid", policy_violations)

    allow_marked_test_credentials = static_config.get("allow_marked_test_credentials", True)
    if not isinstance(allow_marked_test_credentials, bool):
        return blocked_result(
            "static_analysis_config_invalid",
            ["static_analysis.allow_marked_test_credentials deve ser booleano"],
        )
    builtin_findings = scan_hardcoded_secrets(
        root,
        changed_files,
        allow_marked_test_credentials=allow_marked_test_credentials,
    )

    command = static_config.get("adapter_command")
    if command is None:
        result = unavailable_result("adapter_not_configured")
        result["capabilities"] = {"secrets": True}
        return _apply_quality_gate(result, builtin_findings, static_config)
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
    return _apply_quality_gate(result, builtin_findings, static_config)


def write_static_analysis_kpis(root: Path, report: dict[str, Any], config: dict[str, Any]) -> Path:
    """Persiste um snapshot detalhado dos indicadores ao lado do adapter do projeto.
    Mantém os fatos da análise fora dos Draws e evita caminhos absolutos ou segredos no JSON.
    """
    findings = [item for item in report.get("quality_findings", []) if isinstance(item, dict)]
    severity_counts = {
        "blocking": sum(1 for item in findings if item.get("severity") == "blocking"),
        "warning": sum(1 for item in findings if item.get("severity") == "warning"),
    }
    findings_by_kind: dict[str, int] = {}
    for finding in findings:
        kind = str(finding.get("kind", "unknown"))
        findings_by_kind[kind] = findings_by_kind.get(kind, 0) + 1
    symbols = [item for item in report.get("symbols", []) if isinstance(item, dict)]
    dependencies = [item for item in report.get("dependencies", []) if isinstance(item, dict)]
    complexity = [item for item in report.get("complexity", []) if isinstance(item, dict)]
    structural = [item for item in report.get("structural_metrics", []) if isinstance(item, dict)]
    files = sorted({
        str(item.get("file"))
        for collection in (symbols, dependencies, complexity, structural, findings)
        for item in collection
        if item.get("file")
    })
    quality_status = "blocked" if severity_counts["blocking"] else "warning" if severity_counts["warning"] else "healthy"
    static_config = config.get("static_analysis", {}) if isinstance(config.get("static_analysis"), dict) else {}
    applied_exceptions, expired_exceptions = _kpi_exception_counts(report, findings)
    output = {
        "version": STATIC_ANALYSIS_KPI_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": report.get("status", "unavailable"),
        "reason": report.get("reason"),
        "adapter_command": static_config.get("adapter_command"),
        "stack": config.get("stack", {}),
        "indicators": [
            {"id": "symbols", "label": "Símbolos", "value": len(symbols), "unit": "símbolos"},
            {"id": "dependencies", "label": "Dependências", "value": len(dependencies), "unit": "relações"},
            {"id": "files", "label": "Arquivos analisados", "value": len(files), "unit": "arquivos"},
            {"id": "quality_findings", "label": "Achados de qualidade", "value": len(findings), "unit": "achados", "status": quality_status},
            {"id": "blocking_findings", "label": "Bloqueantes", "value": severity_counts["blocking"], "unit": "achados", "status": "blocked" if severity_counts["blocking"] else "healthy"},
            {"id": "applied_exceptions", "label": "Exceções aplicadas", "value": len(applied_exceptions), "unit": "exceções", "status": "warning" if applied_exceptions else "healthy"},
            {"id": "expired_exceptions", "label": "Exceções expiradas", "value": expired_exceptions, "unit": "exceções", "status": "blocked" if expired_exceptions else "healthy"},
        ],
        "summary": {
            "symbols": len(symbols),
            "dependencies": len(dependencies),
            "complexity": len(complexity),
            "structural_metrics": len(structural),
            "files": files,
            "quality_findings": len(findings),
            "severity": severity_counts,
            "findings_by_kind": dict(sorted(findings_by_kind.items())),
            "applied_exceptions": len(applied_exceptions),
            "expired_exceptions": expired_exceptions,
        },
        "capabilities": report.get("capabilities", {}),
        "warnings": report.get("warnings", []),
        "errors": report.get("errors", []),
        "applied_exceptions": applied_exceptions,
        "details": {
            "quality_findings": findings,
            "complexity": complexity,
            "structural_metrics": structural,
            "symbols": symbols,
            "dependencies": dependencies,
            "changes": report.get("changes", []),
        },
    }
    output_path = root / ".stdd" / "adapters" / "static-analysis-kpis.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path
