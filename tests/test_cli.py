from pathlib import Path
import json
import sys

from typer.testing import CliRunner

from stdd.cli import app
from stdd.contract import check_contract
from stdd.core import is_rework_diff, run_tests
from stdd.setup import detect_stack


runner = CliRunner()


def test_test_command_returns_execution_report(tmp_path: Path, monkeypatch):
    """Executa o comando de teste no projeto e valida o relatório retornado.
    Inicializa o projeto no diretório temporário, executa run_tests e valida o status bloqueado.
    """
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    process, report = run_tests(tmp_path)
    assert process.returncode != 0  # no tests exist in the empty project
    assert report["status"] == "blocked"


def test_init_can_install_skills_for_all_supported_agents(tmp_path: Path):
    """Instala as skills nos diretórios dos agentes solicitados pelo usuário.
    Executa init com todas as integrações e confirma que os artefatos continuam separados por agente.
    """
    result = runner.invoke(app, ["init", str(tmp_path), "--all-integrations"])

    assert result.exit_code == 0
    for directory in (".agents", ".claude", ".gemini"):
        assert (tmp_path / directory / "skills" / "setup" / "SKILL.md").exists()


def test_init_interactive_selects_multiple_agent_integrations(tmp_path: Path):
    """Permite escolher várias integrações por números durante a inicialização.
    Simula a seleção de Claude e Gemini e confirma que o setup também pode ser aceito no mesmo fluxo.
    """
    result = runner.invoke(app, ["init", str(tmp_path), "--interactive"], input="2,3\ny\n")

    assert result.exit_code == 0
    assert (tmp_path / ".claude/skills/setup/SKILL.md").exists()
    assert (tmp_path / ".gemini/skills/setup/SKILL.md").exists()
    assert "Selecione" in result.stdout


def test_setup_detects_stack_without_assuming_python(tmp_path: Path):
    """Detecta uma aplicação TypeScript e gera runner compatível com sua stack.
    Cria package.json e confirma que o diagnóstico não escolhe pytest ou outro comando Python.
    """
    (tmp_path / "package.json").write_text('{"scripts":{"test":"vitest run"},"devDependencies":{"vitest":"latest"}}')

    result = runner.invoke(app, ["setup", str(tmp_path)])

    assert result.exit_code == 0
    config = json.loads((tmp_path / ".stdd/config.json").read_text())
    assert config["stack"]["languages"] == ["typescript"]
    assert config["test_commands"][0]["command"] == ["npm", "test"]
    assert "pytest" not in json.dumps(config)
    assert "dist/" in (tmp_path / ".gitignore").read_text()


def test_test_runs_all_configured_suites(tmp_path: Path):
    """Executa todas as suítes de testes configuradas no alias geral do STDD.
    Cria uma configuração com duas suítes em .stdd/config.json e valida o stdout do run_tests.
    """
    (tmp_path / ".stdd").mkdir()
    config = {
        "test_commands": [
            {"name": "unit", "command": [sys.executable, "-c", "print('unit')"]},
            {"name": "integration", "command": [sys.executable, "-c", "print('integration')"]},
        ]
    }
    (tmp_path / ".stdd/config.json").write_text(json.dumps(config))
    process, report = run_tests(tmp_path)
    assert process.returncode == 0
    assert report["status"] == "passed"
    assert "[unit]" in process.stdout
    assert "[integration]" in process.stdout
    assert report["summary"] == {"total": 2, "passed": 2, "failed": 0, "not_executed": 0}
    assert [suite["name"] for suite in report["suites"]] == ["unit", "integration"]


def test_global_test_alias_continues_after_suite_failure(tmp_path: Path):
    """Executa todas as suítes mesmo quando uma delas falha no alias global.
    Configura uma falha antes de uma suíte válida e confirma o relatório consolidado das duas.
    """
    (tmp_path / ".stdd").mkdir()
    config = {
        "test_commands": [
            {"name": "database", "command": [sys.executable, "-c", "raise SystemExit(3)"]},
            {"name": "security", "command": [sys.executable, "-c", "print('security-ran')"]},
        ]
    }
    (tmp_path / ".stdd/config.json").write_text(json.dumps(config))

    process, report = run_tests(tmp_path)

    assert process.returncode == 3
    assert "security-ran" in process.stdout
    assert report["summary"] == {"total": 2, "passed": 1, "failed": 1, "not_executed": 0}
    assert [(suite["name"], suite["status"]) for suite in report["suites"]] == [
        ("database", "failed"),
        ("security", "passed"),
    ]


def test_global_alias_respects_mvp_profile_and_approval_controls(tmp_path: Path):
    """Permite ao MVP pular suítes caras e bloqueia ações que exigem aprovação.
    Configura unitário, banco e performance e confirma os motivos de cada not_executed.
    """
    (tmp_path / ".stdd").mkdir()
    config = {
        "testing": {"profile": "mvp"},
        "test_commands": [
            {"name": "unit", "command": [sys.executable, "-c", "print('unit')"], "profiles": ["mvp"]},
            {"name": "database", "command": [sys.executable, "-c", "raise SystemExit(9)"], "requires_approval": True},
            {"name": "performance", "command": [sys.executable, "-c", "raise SystemExit(9)"], "enabled": False},
        ],
    }
    (tmp_path / ".stdd/config.json").write_text(json.dumps(config))

    process, report = run_tests(tmp_path)

    assert process.returncode == 0
    assert report["profile"] == "mvp"
    assert report["summary"] == {"total": 3, "passed": 1, "failed": 0, "not_executed": 2}
    assert [(suite["name"], suite["status"], suite.get("reason")) for suite in report["suites"]] == [
        ("unit", "passed", None),
        ("database", "not_executed", "approval_required"),
        ("performance", "not_executed", "disabled"),
    ]


def test_global_alias_can_explicitly_run_approved_suite(tmp_path: Path):
    """Executa somente a suíte solicitada quando a ação cara foi aprovada explicitamente.
    Seleciona banco, libera a ação e mantém as demais suítes como não executadas.
    """
    (tmp_path / ".stdd").mkdir()
    config = {
        "testing": {"profile": "mvp"},
        "test_commands": [
            {"name": "unit", "command": [sys.executable, "-c", "print('unit')"]},
            {"name": "database", "command": [sys.executable, "-c", "print('database')"], "requires_approval": True},
        ],
    }
    (tmp_path / ".stdd/config.json").write_text(json.dumps(config))

    process, report = run_tests(tmp_path, include_suites={"database"}, approve_actions=True)

    assert process.returncode == 0
    assert "database" in process.stdout
    assert report["summary"] == {"total": 2, "passed": 1, "failed": 0, "not_executed": 1}
    assert [(suite["name"], suite["status"]) for suite in report["suites"]] == [
        ("unit", "not_executed"),
        ("database", "passed"),
    ]


def test_test_cli_requires_explicit_flag_for_controlled_suite(tmp_path: Path, monkeypatch):
    """Expõe a aprovação de ações controladas no comando público de teste.
    Executa o mesmo runner sem e com a flag e confirma que somente a segunda chamada o libera.
    """
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".stdd").mkdir()
    config = {
        "test_commands": [
            {"name": "database", "command": [sys.executable, "-c", "print('database-executed')"], "requires_approval": True}
        ]
    }
    (tmp_path / ".stdd/config.json").write_text(json.dumps(config))

    denied = runner.invoke(app, ["test", "--suite", "database"])
    approved = runner.invoke(app, ["test", "--suite", "database", "--approve-actions"])

    assert denied.exit_code == 0
    assert "approval_required" in denied.stdout
    assert "database-executed" not in denied.stdout
    assert approved.exit_code == 0
    assert "database-executed" in approved.stdout


def test_test_reports_static_analysis_unavailable_without_adapter(tmp_path: Path):
    """Mantém o teste aprovado quando não existe adaptador estático configurado.
    Executa uma suíte fake e verifica o status explícito unavailable no relatório e na saída.
    """
    (tmp_path / ".stdd").mkdir()
    config = {
        "test_commands": [{"name": "unit", "command": [sys.executable, "-c", "print('unit')"]}],
        "static_analysis": {"enabled": True, "adapter_command": None, "contract_version": "1"},
    }
    (tmp_path / ".stdd/config.json").write_text(json.dumps(config))

    process, report = run_tests(tmp_path)

    assert process.returncode == 0
    assert report["status"] == "passed"
    assert report["static_analysis"]["status"] == "unavailable"
    assert report["static_analysis"]["reason"] == "adapter_not_configured"
    assert "[static-analysis]" in process.stdout


def test_test_executes_fake_static_analysis_adapter(tmp_path: Path):
    """Executa um adaptador fake e incorpora seu relatório factual ao resultado do teste.
    Configura um comando Python que retorna dependências e complexidade em JSON válido.
    """
    (tmp_path / ".stdd").mkdir()
    adapter_result = {
        "contract_version": "1",
        "status": "passed",
        "capabilities": {"dependencies": True, "complexity": True},
        "symbols": [],
        "dependencies": [{"source": "fixture.py", "kind": "imports", "target": "os"}],
        "complexity": [{"symbol_id": "fixture:run", "cyclomatic": 3}],
        "structural_metrics": [],
        "quality_findings": [
            {"kind": "long_function", "severity": "warning", "symbol_id": "fixture:run", "lines": 41}
        ],
        "changes": [],
        "warnings": [],
        "errors": [],
    }
    adapter_code = "import json; print(json.dumps(" + repr(adapter_result) + "))"
    config = {
        "test_commands": [{"name": "unit", "command": [sys.executable, "-c", "print('unit')"]}],
        "static_analysis": {"enabled": True, "adapter_command": [sys.executable, "-c", adapter_code]},
    }
    (tmp_path / ".stdd/config.json").write_text(json.dumps(config))

    process, report = run_tests(tmp_path)

    assert process.returncode == 0
    assert report["static_analysis"]["status"] == "passed"
    assert report["static_analysis"]["dependencies"][0]["target"] == "os"
    assert report["static_analysis"]["complexity"][0]["cyclomatic"] == 3


def test_test_blocks_invalid_static_analysis_output(tmp_path: Path):
    """Bloqueia a execução quando o adaptador não cumpre o schema agnóstico.
    Configura um adaptador que retorna um objeto incompleto e verifica o motivo estruturado.
    """
    (tmp_path / ".stdd").mkdir()
    config = {
        "test_commands": [{"name": "unit", "command": [sys.executable, "-c", "print('unit')"]}],
        "static_analysis": {"adapter_command": [sys.executable, "-c", "print('{}')"]},
    }
    (tmp_path / ".stdd/config.json").write_text(json.dumps(config))

    process, report = run_tests(tmp_path)

    assert process.returncode != 0
    assert report["status"] == "blocked"
    assert report["static_analysis"]["status"] == "blocked"
    assert report["static_analysis"]["reason"] == "adapter_schema_invalid"


def test_test_blocks_blocking_long_function_quality_finding(tmp_path: Path):
    """Bloqueia uma função acima do limite configurado quando o adaptador reporta severidade blocking.
    Retorna um achado long_function válido e verifica que o gate impede a aprovação silenciosa.
    """
    (tmp_path / ".stdd").mkdir()
    adapter_result = {
        "contract_version": "1",
        "status": "passed",
        "capabilities": {"complexity": True},
        "symbols": [],
        "dependencies": [],
        "complexity": [],
        "structural_metrics": [],
        "quality_findings": [
            {
                "kind": "long_function",
                "severity": "blocking",
                "file": "src/service.ext",
                "symbol_id": "service:run",
                "value": 101,
                "limit": 100,
            }
        ],
        "changes": [],
        "warnings": [],
        "errors": [],
    }
    adapter_code = "import json; print(json.dumps(" + repr(adapter_result) + "))"
    config = {
        "test_commands": [{"name": "unit", "command": [sys.executable, "-c", "print('unit')"]}],
        "static_analysis": {"adapter_command": [sys.executable, "-c", adapter_code]},
    }
    (tmp_path / ".stdd/config.json").write_text(json.dumps(config))

    process, report = run_tests(tmp_path)

    assert process.returncode != 0
    assert report["status"] == "blocked"
    assert report["static_analysis"]["status"] == "blocked"
    assert report["static_analysis"]["reason"] == "quality_gate_blocked"


def test_contract_rejects_function_without_short_description(tmp_path: Path):
    """Bloqueia funções de teste Python que não possuem as duas linhas de descrição exigidas.
    Cria um teste sem docstring e verifica se o contrato exige a documentação executável.
    """
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    source = tests_dir / "sample.py"
    source.write_text("def sem_descricao():\n    return True\n")
    violations = check_contract(tmp_path)
    assert "teste sem descrição curta" in violations[0]


def test_contract_rejects_function_with_single_line_docstring(tmp_path: Path):
    """Bloqueia testes Python que possuem apenas uma linha de descrição.
    Cria um teste com uma linha e verifica a violação do formato de duas linhas.
    """
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    source = tests_dir / "sample.py"
    source.write_text('def test_uma_linha():\n    """Apenas o que faz."""\n    return True\n')
    violations = check_contract(tmp_path)
    assert "teste deve ter 2 comentários/linhas" in violations[0]


def test_contract_allows_production_function_without_docstring(tmp_path: Path):
    """Permite funções de produção sem docstring obrigatória.
    Cria um módulo fora de tests e confirma que a documentação executável fica restrita aos testes.
    """
    source = tmp_path / "module.py"
    source.write_text("def calcular():\n    return 42\n")

    assert check_contract(tmp_path) == []


def test_log_command_creates_incremental_summary_and_snapshot_in_date_subfolder(tmp_path: Path, monkeypatch):
    """Registra alteração na subpasta diária com summary e snapshot acumulativos.
    Invoca stdd log e confirma a presença de somente um arquivo de cada tipo.
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["log", "Adiciona nova feature com testes", "-i", "-t"])
    assert result.exit_code == 0
    assert "Registro gravado em" in result.stdout

    day_folders = [p for p in (tmp_path / ".stdd/runs").iterdir() if p.is_dir() and p.name != "data"]
    assert len(day_folders) == 1

    summary_files = list(day_folders[0].glob("*_summary.json"))
    snapshot_files = list(day_folders[0].glob("*_snapshot.json"))
    assert len(summary_files) == 1
    assert len(snapshot_files) == 1

    log_data = json.loads(summary_files[0].read_text(encoding="utf-8"))
    assert log_data["run_count"] == 1
    assert log_data["runs"][0]["description"] == "Adiciona nova feature com testes"
    assert "implementacao" in log_data["runs"][0]["work_types"]
    assert "teste" in log_data["runs"][0]["work_types"]
    snapshot_data = json.loads(snapshot_files[0].read_text(encoding="utf-8"))
    assert snapshot_data["runs"][0]["run_id"] == log_data["runs"][0]["run_id"]
    assert isinstance(snapshot_data["workspace_snapshot"], dict)
    assert not (tmp_path / ".stdd/latest_snapshot.json").exists()
    assert not (tmp_path / ".stdd/runs/data/latest_snapshot.json").exists()


def test_log_accumulates_runs_in_one_summary_and_snapshot_per_day(tmp_path: Path, monkeypatch):
    """Mantém somente um summary e um snapshot e acumula as duas execuções.
    Executa dois registros no mesmo dia e verifica que os relatórios preservam ambos os run_id.
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])

    first = runner.invoke(app, ["log", "Primeiro registro", "-i"])
    day_folder = next(path for path in (tmp_path / ".stdd/runs").iterdir() if path.is_dir() and path.name != "data")
    (day_folder / "125000_old_summary.json").write_text("{}", encoding="utf-8")
    (day_folder / "125000_old_snapshot.json").write_text("{}", encoding="utf-8")
    second = runner.invoke(app, ["log", "Segundo registro", "-t"])

    assert first.exit_code == 0
    assert second.exit_code == 0
    day = day_folder.name
    assert sorted(path.name for path in day_folder.iterdir()) == [
        f"{day}_snapshot.json",
        f"{day}_summary.json",
    ]

    summary = json.loads((day_folder / f"{day}_summary.json").read_text(encoding="utf-8"))
    snapshot = json.loads((day_folder / f"{day}_snapshot.json").read_text(encoding="utf-8"))
    assert summary["run_count"] == 2
    assert [run["description"] for run in summary["runs"]] == ["Primeiro registro", "Segundo registro"]
    assert snapshot["run_count"] == 2
    assert [run["run_id"] for run in snapshot["runs"]] == [run["run_id"] for run in summary["runs"]]
    assert not (tmp_path / ".stdd/latest_snapshot.json").exists()
    assert not (tmp_path / ".stdd/runs/data/latest_snapshot.json").exists()


def test_log_migrates_legacy_daily_documents_before_appending(tmp_path: Path, monkeypatch):
    """Converte o formato diário antigo para a lista incremental sem perder a execução anterior.
    Cria documentos legados e confirma que o novo registro preserva ambos os run_id.
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    day = "2026-07-31"
    day_folder = tmp_path / ".stdd/runs" / day
    day_folder.mkdir(parents=True)
    (day_folder / f"{day}_summary.json").write_text(
        json.dumps({"run_id": "legacy-summary", "timestamp": "2026-07-31T10:00:00+00:00", "description": "Legado", "work_types": ["teste"], "diff_stats": {}}),
        encoding="utf-8",
    )
    (day_folder / f"{day}_snapshot.json").write_text(
        json.dumps({"run_id": "legacy-snapshot", "timestamp": "2026-07-31T10:00:00+00:00", "files": []}),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["log", "Novo registro", "-i"])

    assert result.exit_code == 0
    summary = json.loads((day_folder / f"{day}_summary.json").read_text(encoding="utf-8"))
    snapshot = json.loads((day_folder / f"{day}_snapshot.json").read_text(encoding="utf-8"))
    assert [run["run_id"] for run in summary["runs"]] == ["legacy-summary", summary["runs"][-1]["run_id"]]
    assert [run["run_id"] for run in snapshot["runs"]] == ["legacy-snapshot", snapshot["runs"][-1]["run_id"]]


def test_log_marks_large_incremental_change_as_refactor(tmp_path: Path, monkeypatch):
    """Classifica uma alteração incremental grande como refactor automaticamente.
    Registra um baseline e depois substitui muitas linhas para validar o work_type adicional.
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    source = tmp_path / "large.py"
    source.write_text("\n".join(f"value_{index} = {index}" for index in range(520)) + "\n")
    baseline = runner.invoke(app, ["log", "Registra baseline", "-i"])
    source.write_text("\n".join(f"value_{index} = {index + 1}" for index in range(520)) + "\n")

    result = runner.invoke(app, ["log", "Reorganiza grande bloco", "-i"])

    assert baseline.exit_code == 0
    assert result.exit_code == 0
    day_folder = next(path for path in (tmp_path / ".stdd/runs").iterdir() if path.is_dir() and path.name != "data")
    summary = json.loads(next(day_folder.glob("*_summary.json")).read_text(encoding="utf-8"))
    last_run = summary["runs"][-1]
    assert "refactor" in last_run["work_types"]
    assert last_run["diff_stats"]["lines_added"] == 520
    assert last_run["diff_stats"]["lines_deleted"] == 520


def test_log_does_not_classify_medium_replacement_as_refactor():
    """Mantém uma substituição média sem classificação automática de refactor.
    Confirma que 120 linhas adicionadas e removidas exigem avaliação contextual do agente.
    """
    assert not is_rework_diff({"lines_added": 120, "lines_deleted": 120})


def test_log_command_respects_custom_tracked_extensions(tmp_path: Path, monkeypatch):
    """Respeita as extensões rastreadas customizadas no arquivo .stdd/config.json.
    Adiciona .md às extensões rastreadas, modifica um arquivo markdown e valida no snapshot.
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    config_path = tmp_path / ".stdd/config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["tracked_extensions"] = [".py", ".md"]
    config_path.write_text(json.dumps(config), encoding="utf-8")

    doc_file = tmp_path / "doc.md"
    doc_file.write_text("# Especificação\nLinha 1\n")

    result = runner.invoke(app, ["log", "Atualiza documentação markdown", "-i"])
    assert result.exit_code == 0

    day_folder = next(path for path in (tmp_path / ".stdd/runs").iterdir() if path.is_dir() and path.name != "data")
    snapshot_file = list(day_folder.glob("*_snapshot.json"))[0]
    snapshot_data = json.loads(snapshot_file.read_text(encoding="utf-8"))
    modified_paths = [f["path"] for f in snapshot_data["runs"][-1]["files"]]
    assert "doc.md" in modified_paths


def test_log_snapshot_includes_unified_diff_for_modified_file(tmp_path: Path, monkeypatch):
    """Inclui o patch textual junto das métricas de linhas de um arquivo alterado.
    Cria um baseline, modifica uma linha e verifica o unified diff persistido no snapshot.
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    source = tmp_path / "example.py"
    source.write_text("def answer():\n    return 1\n")
    runner.invoke(app, ["log", "Baseline da resposta", "-i"])

    source.write_text("def answer():\n    return 2\n")
    result = runner.invoke(app, ["log", "Atualiza resposta", "-i"])

    assert result.exit_code == 0
    day_folder = next(path for path in (tmp_path / ".stdd/runs").iterdir() if path.is_dir() and path.name != "data")
    snapshots = list(day_folder.glob("*_snapshot.json"))
    assert len(snapshots) == 1
    snapshot_data = json.loads(snapshots[0].read_text(encoding="utf-8"))
    changed_file = next(item for item in snapshot_data["runs"][-1]["files"] if item["path"] == "example.py")

    assert changed_file["lines_added"] == 1
    assert changed_file["lines_deleted"] == 1
    assert changed_file["diff"] == (
        "--- a/example.py\n"
        "+++ b/example.py\n"
        "@@ -1,2 +1,2 @@\n"
        " def answer():\n"
        "-    return 1\n"
        "+    return 2"
    )


def test_log_snapshot_includes_diffs_for_created_and_deleted_files(tmp_path: Path, monkeypatch):
    """Representa criação e remoção de arquivos com patches textuais completos.
    Registra um baseline e depois troca dois arquivos, validando os cabeçalhos e conteúdos do diff.
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    deleted = tmp_path / "deleted.py"
    deleted.write_text("return_value = 1\n")
    runner.invoke(app, ["log", "Baseline dos arquivos", "-i"])

    deleted.unlink()
    created = tmp_path / "created.py"
    created.write_text("return_value = 2\n")
    result = runner.invoke(app, ["log", "Troca arquivos", "-i"])

    assert result.exit_code == 0
    day_folder = next(path for path in (tmp_path / ".stdd/runs").iterdir() if path.is_dir() and path.name != "data")
    snapshot_data = json.loads(sorted(day_folder.glob("*_snapshot.json"))[-1].read_text(encoding="utf-8"))
    files = {item["path"]: item for item in snapshot_data["runs"][-1]["files"]}

    assert files["deleted.py"]["diff"] == (
        "--- a/deleted.py\n"
        "+++ b/deleted.py\n"
        "@@ -1 +0,0 @@\n"
        "-return_value = 1"
    )
    assert files["created.py"]["diff"] == (
        "--- a/created.py\n"
        "+++ b/created.py\n"
        "@@ -0,0 +1 @@\n"
        "+return_value = 2"
    )


def test_log_command_requires_at_least_one_work_type(tmp_path: Path, monkeypatch):
    """Rejeita comandos stdd log sem informar nenhum tipo de trabalho.
    Invoca stdd log sem flags -i, -t, -b ou -r e valida a mensagem de erro.
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["log", "Descrição sem tipo"])
    assert result.exit_code != 0
    assert "Ao menos um tipo de trabalho deve ser informado" in result.stderr
