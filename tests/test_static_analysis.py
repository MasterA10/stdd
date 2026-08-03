import json
from pathlib import Path

from stdd.static_analysis import run_static_analysis, scan_hardcoded_secrets, write_static_analysis_kpis


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
