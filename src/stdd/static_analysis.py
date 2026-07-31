"""Contratos e execução segura de adaptadores de análise estática.
Define o protocolo JSON agnóstico de linguagem usado pelo comando `stdd test`.
"""

from __future__ import annotations

import json
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

    command = static_config.get("adapter_command")
    if command is None:
        return unavailable_result("adapter_not_configured")
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
