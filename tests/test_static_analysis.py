import json
from pathlib import Path
import sys

from stdd.core import run_tests
from stdd.static_analysis import run_static_analysis, scan_hardcoded_secrets, write_static_analysis_kpis


def _adapter_command(result: dict) -> list[str]:
    """Monta um comando de adapter fake para devolver um relatório conhecido.
    Serializa o resultado sem depender de arquivos ou ferramentas frontend.
    """
    return [sys.executable, "-c", "import json; print(json.dumps(" + repr(result) + "))"]


def test_secret_scanner_detects_hardcoded_password_without_leaking_value(tmp_path: Path):
    """Detecta senha literal no código e redige o valor no achado.
    Cria um módulo com credencial falsa e confirma o tipo, linha e ausência do segredo.
    """
    source = tmp_path / "settings.py"
    secret_value = "super" + "-secret-value-123"
    source.write_text("PASS" + "WORD = " + '"' + secret_value + '"\n')

    findings = scan_hardcoded_secrets(tmp_path, ["settings.py"])

    assert len(findings) == 1
    assert findings[0]["kind"] == "hardcoded_secret"
    assert findings[0]["severity"] == "blocking"
    assert findings[0]["file"] == "settings.py"
    assert findings[0]["line"] == 1
    assert findings[0]["value"] == "[REDACTED]"
    assert "super-secret-value-123" not in str(findings[0])


def test_secret_scanner_ignores_environment_lookup_and_placeholders(tmp_path: Path):
    """Não acusa leitura de ambiente nem placeholders não secretos.
    Escreve padrões seguros e confirma que a análise não produz falso positivo.
    """
    source = tmp_path / "settings.py"
    source.write_text(
        'PASSWORD = os.getenv("PASSWORD")\n'
        'API_KEY = "test"\n'
        'TOKEN = "${TOKEN}"\n'
    )

    assert scan_hardcoded_secrets(tmp_path, ["settings.py"]) == []


def test_secret_scanner_ignores_local_secret_fixture_in_test_file(tmp_path: Path):
    """Não bloqueia segredos sintéticos de testes de contrato.
    Mantém o bloqueio para atribuições equivalentes em arquivos de produção.
    """
    source = tmp_path / "tests/CoreContractsTest.php"
    source.parent.mkdir()
    source.write_text("<?php\n$secret = 'meta-app-secret';\n")

    assert scan_hardcoded_secrets(tmp_path, ["tests/CoreContractsTest.php"]) == []

    production = tmp_path / "src/Config.php"
    production.parent.mkdir()
    production.write_text("<?php\n$secret = 'production-secret-value';\n")
    assert scan_hardcoded_secrets(tmp_path, ["src/Config.php"])[0]["kind"] == "hardcoded_secret"


def test_secret_scanner_warns_for_explicitly_allowed_test_credential(tmp_path: Path):
    """Mantém visível, mas não bloqueia, uma credencial fictícia marcada no teste.
    A anotação precisa estar no fixture de teste e o valor continua redigido.
    """
    source = tmp_path / "tests/credentials_test.py"
    source.parent.mkdir()
    source.write_text('PASSWORD = "ced-ficticia-123456"  # stdd:allow-credential\n')

    findings = scan_hardcoded_secrets(tmp_path, ["tests/credentials_test.py"])

    assert findings[0]["kind"] == "hardcoded_secret"
    assert findings[0]["severity"] == "warning"
    assert findings[0]["exception"] == "explicit_test_credential_allowlist"
    assert findings[0]["value"] == "[REDACTED]"
    assert "ced-ficticia-123456" not in str(findings[0])


def test_secret_scanner_does_not_allow_marker_in_production_file(tmp_path: Path):
    """Não transforma uma anotação fora de teste em permissão silenciosa.
    Confirma que a mesma marca continua bloqueante em código de produção.
    """
    source = tmp_path / "src/settings.py"
    source.parent.mkdir()
    source.write_text('PASSWORD = "ced-ficticia-123456"  # stdd:allow-credential\n')

    findings = scan_hardcoded_secrets(tmp_path, ["src/settings.py"])

    assert findings[0]["severity"] == "blocking"
    assert "exception" not in findings[0]


def test_static_analysis_can_disable_marked_test_credential_exceptions(tmp_path: Path):
    """Permite que um projeto imponha bloqueio mesmo em fixtures marcadas.
    Executa a análise com a política rígida e verifica a severidade bloqueante.
    """
    source = tmp_path / "tests/credentials_test.py"
    source.parent.mkdir()
    source.write_text('PASSWORD = "ced-ficticia-123456"  # stdd:allow-credential\n')

    report = run_static_analysis(
        tmp_path,
        "execution-credentials",
        {"static_analysis": {"allow_marked_test_credentials": False}},
        ["tests/credentials_test.py"],
    )

    assert report["status"] == "blocked"
    assert report["quality_findings"][0]["severity"] == "blocking"


def test_static_analysis_passes_gate_for_marked_test_credential(tmp_path: Path):
    """Mantém o gate aprovado quando a exceção explícita transforma o achado em warning.
    Usa uma fixture marcada e verifica que o valor continua redigido no relatório.
    """
    source = tmp_path / "tests/credentials_test.py"
    source.parent.mkdir()
    source.write_text('PASSWORD = "ced-ficticia-123456"  # stdd:allow-credential\n')

    report = run_static_analysis(
        tmp_path,
        "execution-credentials-allowed",
        {"static_analysis": {"allow_marked_test_credentials": True}},
        ["tests/credentials_test.py"],
    )

    assert report["status"] == "unavailable"
    assert report["quality_findings"][0]["severity"] == "warning"


def test_stdd_test_passes_with_marked_test_credential_and_keeps_warning(tmp_path: Path):
    """Confirma o comportamento completo do gate global, não apenas do scanner.
    Executa uma suíte fake e preserva o warning de credencial permitido.
    """
    source = tmp_path / "tests/credentials_test.py"
    source.parent.mkdir()
    source.write_text('PASSWORD = "ced-ficticia-123456"  # stdd:allow-credential\n')
    (tmp_path / ".stdd").mkdir()
    (tmp_path / ".stdd/config.json").write_text(json.dumps({
        "test_commands": [{"name": "unit", "command": ["python3", "-c", "print('unit')"]}],
        "static_analysis": {
            "enabled": True,
            "adapter_command": None,
            "allow_marked_test_credentials": True,
        },
    }))

    process, report = run_tests(tmp_path)

    assert process.returncode == 0
    assert report["status"] == "passed"
    assert report["static_analysis"]["quality_findings"][0]["severity"] == "warning"


def test_static_analysis_blocks_hardcoded_secret_without_external_adapter(tmp_path: Path):
    """Bloqueia segredo hardcoded mesmo sem adapter externo configurado.
    Executa a análise built-in e confirma que o relatório não transforma o achado em indisponível aprovado.
    """
    source = tmp_path / "settings.py"
    secret_value = "database" + "-password-123"
    source.write_text("DATABASE_" + "PASSWORD = " + '"' + secret_value + '"\n')

    report = run_static_analysis(tmp_path, "execution-1", {}, ["settings.py"])

    assert report["status"] == "blocked"
    assert report["reason"] == "hardcoded_secret"
    assert report["quality_findings"][0]["kind"] == "hardcoded_secret"


def test_static_analysis_warns_for_level_two_nodes_without_code_refs(tmp_path: Path):
    """Inclui o contrato de rastreabilidade do nível 2 no relatório estático.
    O warning é produzido pelo núcleo mesmo sem adapter externo e não bloqueia o gate.
    """
    draws = tmp_path / ".stdd" / "draws"
    draws.mkdir(parents=True)
    payload = {
        "id": "journey-contract",
        "title": "Jornada",
        "kind": "system",
        "hierarchy": {"level": 2, "role": "journey", "root_draw_ref": "root"},
        "nodes": [{"id": 1, "label": "Tela"}],
        "edges": [],
    }
    (draws / "journey-contract.json").write_text(json.dumps(payload), encoding="utf-8")

    report = run_static_analysis(tmp_path, "execution-draw-contract", {}, [])

    assert report["status"] == "unavailable"
    assert report["quality_findings"][0]["kind"] == "draw.level2_missing_code_ref"
    assert report["quality_findings"][0]["severity"] == "warning"


def test_static_analysis_writes_kpi_snapshot_next_to_adapter_directory(tmp_path: Path):
    """Persiste indicadores agregados e detalhes sem misturar com os Draws.
    Reúne um relatório mínimo e confirma a estrutura consumida pelo viewer lateral.
    """
    report = {
        "status": "blocked",
        "reason": "quality_gate_blocked",
        "capabilities": {"symbols": True},
        "symbols": [{"qualified_name": "demo.run", "file": "src/demo.py"}],
        "dependencies": [],
        "complexity": [],
        "structural_metrics": [],
        "quality_findings": [{"kind": "long_function", "severity": "blocking", "file": "src/demo.py"}],
        "changes": [],
        "warnings": [],
        "errors": ["quality gate"],
    }

    output = write_static_analysis_kpis(tmp_path, report, {"static_analysis": {"adapter_command": ["python", "adapter.py"]}})

    assert output == tmp_path / ".stdd/adapters/static-analysis-kpis.json"
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["indicators"][0]["value"] == 1
    assert saved["summary"]["severity"]["blocking"] == 1
    assert saved["details"]["quality_findings"][0]["kind"] == "long_function"
    assert not (tmp_path / ".stdd/draws").exists()


def test_secret_scanner_detects_env_value_copied_into_source_without_leaking_value(tmp_path: Path):
    """Detecta valor definido em arquivo de ambiente e repetido no código.
    Confirma que a sincronização bloqueia o vazamento sem devolver o valor original.
    """
    (tmp_path / ".env.local").write_text("PAYMENT_KEY=env-secret-value-123\n")
    source = tmp_path / "settings.py"
    source.write_text('PAYMENT_KEY = "env-secret-value-123"\n')

    findings = scan_hardcoded_secrets(tmp_path, ["settings.py"])

    assert len(findings) == 1
    assert findings[0]["kind"] == "hardcoded_env_value"
    assert findings[0]["env_key"] == "PAYMENT_KEY"
    assert findings[0]["value"] == "[REDACTED]"
    assert "env-secret-value-123" not in str(findings[0])


def test_secret_scanner_reports_env_key_without_code_reference(tmp_path: Path):
    """Relata variável de ambiente sem uso detectável no código.
    Mantém o diagnóstico como aviso para não bloquear configurações legítimas de infraestrutura.
    """
    (tmp_path / ".env").write_text("UNUSED_SERVICE_TOKEN=secret-value-123\n")
    source = tmp_path / "settings.py"
    source.write_text("VALUE = 1\n")

    findings = scan_hardcoded_secrets(tmp_path, ["settings.py"])

    assert findings == [{
        "kind": "unreferenced_env_variable",
        "severity": "warning",
        "file": ".env",
        "env_key": "UNUSED_SERVICE_TOKEN",
        "value": "[REDACTED]",
        "evidence": "environment variable has no code reference",
        "source": "builtin_secret_scanner",
    }]


def test_frontend_static_finding_blocks_only_when_frontend_policy_is_enabled(tmp_path: Path):
    """Aplica o gate frontend somente quando a política foi habilitada.
    Usa um finding estático de referência morta e compara disabled com blocking.
    """
    result = {
        "contract_version": "1",
        "status": "passed",
        "capabilities": {"frontend": True},
        "symbols": [],
        "dependencies": [],
        "complexity": [],
        "structural_metrics": [],
        "quality_findings": [{
            "domain": "frontend",
            "rule": "frontend.dead_reference",
            "kind": "frontend_dead_reference",
            "severity": "blocking",
            "file": "src/App.tsx",
            "line": 12,
            "value": "/missing",
            "limit": 0,
            "evidence": "literal destination does not exist",
        }],
        "changes": [],
        "warnings": [],
        "errors": [],
    }

    disabled = run_static_analysis(
        tmp_path,
        "frontend-disabled",
        {"static_analysis": {"adapter_command": _adapter_command(result)}},
        [],
    )
    assert disabled["status"] == "passed"
    assert disabled["quality_findings"] == []

    blocking = run_static_analysis(
        tmp_path,
        "frontend-blocking",
        {"static_analysis": {
            "frontend": {"enabled": True},
            "adapter_command": _adapter_command(result),
        }},
        [],
    )
    assert blocking["status"] == "blocked"
    assert blocking["quality_findings"][0]["rule"] == "frontend.dead_reference"


def test_frontend_warning_mode_downgrades_static_findings(tmp_path: Path):
    """Permite revisar findings frontend sem interromper a suíte.
    Mantém a evidência e converte somente a severidade bloqueante em aviso.
    """
    result = {
        "contract_version": "1",
        "status": "passed",
        "capabilities": {"frontend": True},
        "symbols": [], "dependencies": [], "complexity": [], "structural_metrics": [],
        "quality_findings": [{
            "domain": "frontend",
            "rule": "frontend.interactive_without_action",
            "kind": "frontend_interactive_without_action",
            "severity": "blocking",
            "file": "src/Menu.vue",
            "line": 8,
        }],
        "changes": [], "warnings": [], "errors": [],
    }
    report = run_static_analysis(
        tmp_path,
        "frontend-warning",
        {"static_analysis": {
            "frontend": {"enabled": True, "mode": "warning"},
            "adapter_command": _adapter_command(result),
        }},
        [],
    )

    assert report["status"] == "passed"
    assert report["quality_findings"][0]["severity"] == "warning"
    assert report["quality_findings"][0]["policy"] == "frontend_warning_mode"


def test_static_analysis_exception_downgrades_and_records_frontend_finding(tmp_path: Path):
    """Aceita uma exceção temporária sem apagar a evidência do finding.
    Aponta a exceção para um arquivo e confirma motivo operacional no relatório.
    """
    result = {
        "contract_version": "1", "status": "passed", "capabilities": {"frontend": True},
        "symbols": [], "dependencies": [], "complexity": [], "structural_metrics": [],
        "quality_findings": [{
            "domain": "frontend", "rule": "frontend.dead_reference",
            "kind": "frontend_dead_reference", "severity": "blocking",
            "file": "src/Legacy.tsx", "line": 10,
        }],
        "changes": [], "warnings": [], "errors": [],
    }
    report = run_static_analysis(
        tmp_path,
        "frontend-exception",
        {"static_analysis": {
            "frontend": {"enabled": True},
            "exceptions": [{
                "rule": "frontend.dead_reference",
                "file": "src/Legacy.tsx",
                "action": "warning",
                "reason": "Destino controlado por CMS.",
                "expires": "2099-01-01",
            }],
            "adapter_command": _adapter_command(result),
        }},
        [],
    )

    assert report["status"] == "passed"
    assert report["quality_findings"][0]["severity"] == "warning"
    assert report["quality_findings"][0]["exception_applied"] == "exception-1"
    assert report["applied_exceptions"][0]["action"] == "warning"


def test_static_analysis_ignore_exception_removes_active_finding_but_keeps_evidence(tmp_path: Path):
    """Remove um finding explicitamente ignorado dos indicadores ativos.
    Mantém a identidade da exceção aplicada para auditoria do projeto.
    """
    result = {
        "contract_version": "1", "status": "passed", "capabilities": {"frontend": True},
        "symbols": [], "dependencies": [], "complexity": [], "structural_metrics": [],
        "quality_findings": [{
            "domain": "frontend", "rule": "frontend.missing_destination",
            "kind": "frontend_missing_destination", "severity": "blocking",
            "file": "src/ExternalLink.js", "line": 4,
        }],
        "changes": [], "warnings": [], "errors": [],
    }
    report = run_static_analysis(
        tmp_path,
        "frontend-ignore",
        {"static_analysis": {
            "frontend": {"enabled": True},
            "exceptions": [{
                "rule": "frontend.missing_destination",
                "lines": [4, 4],
                "action": "ignore",
                "reason": "Destino fornecido por integração externa.",
                "expires": "2099-01-01",
            }],
            "adapter_command": _adapter_command(result),
        }},
        [],
    )

    assert report["status"] == "passed"
    assert report["quality_findings"] == []
    assert report["applied_exceptions"][0]["action"] == "ignore"


def test_expired_static_analysis_exception_blocks(tmp_path: Path):
    """Bloqueia exceções vencidas em vez de permitir dívida silenciosa.
    Usa uma data passada e confirma o finding específico de expiração.
    """
    report = run_static_analysis(
        tmp_path,
        "expired-exception",
        {"static_analysis": {
            "exceptions": [{
                "rule": "frontend.dead_reference", "file": "src/Legacy.tsx",
                "action": "warning", "reason": "Revisar compatibilidade.", "expires": "2020-01-01",
            }],
            "adapter_command": None,
        }},
        [],
    )

    assert report["status"] == "blocked"
    assert report["quality_findings"][0]["kind"] == "static_analysis.exception_expired"


def test_static_analysis_rejects_invalid_exception_policy(tmp_path: Path):
    """Rejeita exceções sem alvo ou validade em vez de ignorar a configuração.
    Mantém o gate bloqueado quando a política não é determinística.
    """
    report = run_static_analysis(
        tmp_path,
        "invalid-exception",
        {"static_analysis": {"exceptions": [{"rule": "frontend.dead_reference", "action": "ignore"}]}},
        [],
    )

    assert report["status"] == "blocked"
    assert report["reason"] == "static_analysis_config_invalid"


def test_static_analysis_exceptions_do_not_release_hardcoded_secrets(tmp_path: Path):
    """Mantém segredo hardcoded bloqueante mesmo com exceção correspondente.
    Confirma que a política de exceções não enfraquece o scanner de segurança interno.
    """
    source = tmp_path / "settings.py"
    source.write_text('PASSWORD = "production-secret-value"\n')
    report = run_static_analysis(
        tmp_path,
        "protected-exception",
        {"static_analysis": {
            "exceptions": [{
                "rule": "hardcoded_secret", "file": "settings.py", "action": "ignore",
                "reason": "Não deve ser permitido.", "expires": "2099-01-01",
            }],
        }},
        ["settings.py"],
    )

    assert report["status"] == "blocked"
    assert report["quality_findings"][0]["kind"] == "hardcoded_secret"
    assert report["applied_exceptions"] == []
