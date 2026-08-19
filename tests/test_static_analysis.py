import json
import runpy
from pathlib import Path
import sys

from looper.core import run_tests
from looper.static_analysis import run_static_analysis, scan_hardcoded_secrets, write_static_analysis_kpis


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
    source.write_text('PASSWORD = "ced-ficticia-123456"  # looper:allow-credential\n')

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
    source.write_text('PASSWORD = "ced-ficticia-123456"  # looper:allow-credential\n')

    findings = scan_hardcoded_secrets(tmp_path, ["src/settings.py"])

    assert findings[0]["severity"] == "blocking"
    assert "exception" not in findings[0]


def test_static_analysis_can_disable_marked_test_credential_exceptions(tmp_path: Path):
    """Permite que um projeto imponha bloqueio mesmo em fixtures marcadas.
    Executa a análise com a política rígida e verifica a severidade bloqueante.
    """
    source = tmp_path / "tests/credentials_test.py"
    source.parent.mkdir()
    source.write_text('PASSWORD = "ced-ficticia-123456"  # looper:allow-credential\n')

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
    source.write_text('PASSWORD = "ced-ficticia-123456"  # looper:allow-credential\n')

    report = run_static_analysis(
        tmp_path,
        "execution-credentials-allowed",
        {"static_analysis": {"allow_marked_test_credentials": True}},
        ["tests/credentials_test.py"],
    )

    assert report["status"] == "unavailable"
    assert report["quality_findings"][0]["severity"] == "warning"


def test_looper_test_passes_with_marked_test_credential_and_keeps_warning(tmp_path: Path):
    """Confirma o comportamento completo do gate global, não apenas do scanner.
    Executa uma suíte fake e preserva o warning de credencial permitido.
    """
    source = tmp_path / "tests/credentials_test.py"
    source.parent.mkdir()
    source.write_text('PASSWORD = "ced-ficticia-123456"  # looper:allow-credential\n')
    (tmp_path / ".looper").mkdir()
    (tmp_path / ".looper/config.json").write_text(json.dumps({
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
    O achado é produzido pelo núcleo mesmo sem adapter externo e bloqueia o gate.
    """
    draws = tmp_path / ".looper" / "draws"
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

    assert report["status"] == "blocked"
    assert report["quality_findings"][0]["kind"] == "draw.level2_missing_code_ref"
    assert report["quality_findings"][0]["severity"] == "blocking"


def test_looper_test_blocks_frontend_flow_without_symbols(tmp_path: Path):
    """Bloqueia o gate global quando uma jornada frontend não possui símbolos.
    Executa uma suíte válida e confirma que o Draw inválido impede o sucesso silencioso.
    """
    draws = tmp_path / ".looper" / "draws"
    draws.mkdir(parents=True)
    payload = {
        "id": "frontend-sem-simbolos",
        "title": "Jornada sem símbolos",
        "kind": "system",
        "hierarchy": {"level": 2, "role": "journey", "root_draw_ref": "root"},
        "nodes": [{"id": 1, "label": "Tela sem referência"}],
        "edges": [],
    }
    (draws / "frontend-sem-simbolos.json").write_text(json.dumps(payload), encoding="utf-8")
    (tmp_path / ".looper" / "config.json").write_text(json.dumps({
        "test_commands": [{"name": "unit", "command": [sys.executable, "-c", "print('unit')"]}],
        "static_analysis": {"enabled": True, "adapter_command": None},
    }), encoding="utf-8")

    process, report = run_tests(tmp_path)

    assert process.returncode != 0
    assert report["status"] == "blocked"
    assert report["static_analysis"]["status"] == "blocked"
    finding = report["static_analysis"]["quality_findings"][0]
    assert finding["kind"] == "draw.level2_missing_code_ref"
    assert finding["severity"] == "blocking"


def test_static_adapter_keeps_tsx_filename_when_extracting_symbols(tmp_path: Path, monkeypatch):
    """Extrai símbolos de uma classe TSX sem remover parte do nome do arquivo.
    Executa o dispatcher e o adapter TypeScript com ErroImportacaoView.tsx.
    """
    adapters = tmp_path / ".looper" / "adapters"
    adapters.mkdir(parents=True)
    dispatcher = adapters / "static_adapter.py"
    dispatcher.write_text(Path("src/looper/templates/adapters/static_adapter.py").read_text(encoding="utf-8"), encoding="utf-8")
    (adapters / "js_ts_static_adapter.js").write_text(Path("src/looper/templates/adapters/js_ts_static_adapter.js").read_text(encoding="utf-8"), encoding="utf-8")
    source = tmp_path / "src" / "views" / "ErroImportacaoView.tsx"
    source.parent.mkdir(parents=True)
    source.write_text(
        "import React from 'react';\n"
        "export class ErroImportacaoView extends React.Component {\n"
        "  render() { return <div>Erro</div>; }\n"
        "}\n",
        encoding="utf-8",
    )
    adapter_module = runpy.run_path("src/looper/templates/adapters/static_adapter.py")
    assert adapter_module["module_from_path"](tmp_path, source) == "views.ErroImportacaoView"
    monkeypatch.setenv("NODE_PATH", str(Path("draw-editor/node_modules").resolve()))

    report = run_static_analysis(
        tmp_path,
        "execution-tsx-symbol",
        {"static_analysis": {"adapter_command": [sys.executable, str(dispatcher)]}},
        ["src/views/ErroImportacaoView.tsx"],
    )

    assert report["status"] == "passed"
    assert any(
        symbol["file"] == "src/views/ErroImportacaoView.tsx"
        and symbol["qualified_name"] == "ErroImportacaoView"
        for symbol in report["symbols"]
    )


def test_static_analysis_includes_draw_node_symbol_warnings(tmp_path: Path):
    """Inclui achados de símbolos de nós vazios e duplicados no relatório estático.
    Executa a análise e confirma bloqueio para ausência e aviso para duplicação.
    """
    draws = tmp_path / ".looper" / "draws"
    draws.mkdir(parents=True)
    payload = {
        "version": 1,
        "id": "symbol-warnings-draw",
        "title": "Desenho com avisos de símbolos",
        "nodes": [
            {"id": 1, "label": "Passo 1", "code_refs": [{"symbol": ""}]},
            {"id": 2, "label": "Passo 2", "code_refs": [{"symbol": "same_symbol"}]},
            {"id": 3, "label": "Passo 3", "code_refs": [{"symbol": "same_symbol"}]},
            {"id": 4, "label": "Passo 4", "code_refs": [{"symbol": "same_symbol"}]},
            {"id": 5, "label": "Passo 5", "code_refs": [{"symbol": "same_symbol"}]},
            {"id": 6, "label": "Passo 6", "code_refs": [{"symbol": "same_symbol"}]},
        ],
        "edges": [],
    }
    (draws / "symbol-warnings-draw.json").write_text(json.dumps(payload), encoding="utf-8")

    report = run_static_analysis(tmp_path, "exec-symbols", {}, [])

    kinds = [finding["kind"] for finding in report["quality_findings"]]
    assert "draw.empty_node_symbol" in kinds
    assert "draw.duplicate_node_symbol" in kinds
    assert report["status"] == "blocked"
    assert {f["kind"]: f["severity"] for f in report["quality_findings"]} == {
        "draw.empty_node_symbol": "blocking",
        "draw.duplicate_node_symbol": "warning",
    }



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

    assert output == tmp_path / ".looper/adapters/static-analysis-kpis.json"
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["indicators"][0]["value"] == 1
    assert saved["summary"]["severity"]["blocking"] == 1
    assert saved["details"]["quality_findings"][0]["kind"] == "long_function"
    assert not (tmp_path / ".looper/draws").exists()


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


def test_expired_static_analysis_exception_blocks(tmp_path: Path):
    """Bloqueia exceções vencidas em vez de permitir dívida silenciosa.
    Usa uma data passada e confirma o finding específico de expiração.
    """
    report = run_static_analysis(
        tmp_path,
        "expired-exception",
        {"static_analysis": {
            "exceptions": [{
                "rule": "long_function", "file": "src/service.py",
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
        {"static_analysis": {"exceptions": [{"rule": "long_function", "action": "ignore"}]}},
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
