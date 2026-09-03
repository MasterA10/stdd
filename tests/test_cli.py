from datetime import datetime, timezone
from pathlib import Path
import json
import shutil
import subprocess
import sys

import pytest
import yaml

from typer.testing import CliRunner

from looper.cli import app
from looper.contract import check_contract
from looper.core import get_workspace_snapshot, is_rework_diff, run_tests
from looper.setup import detect_stack


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
    test_report = next((tmp_path / ".looper/runs").glob("*/*_tests.json"))
    saved = json.loads(test_report.read_text(encoding="utf-8"))
    assert saved["status"] == "blocked"
    index = json.loads((tmp_path / ".looper/runs/index.json").read_text(encoding="utf-8"))
    assert index["days"][0]["test_report"].endswith("_tests.json")


def test_init_can_install_skills_for_all_supported_agents(tmp_path: Path):
    """Instala as skills nos diretórios dos agentes solicitados pelo usuário.
    Executa init com todas as integrações e confirma que os artefatos continuam separados por agente.
    """
    result = runner.invoke(app, ["init", str(tmp_path), "--all-integrations"])

    assert result.exit_code == 0
    for directory in (".agents", ".claude", ".gemini"):
        assert (tmp_path / directory / "skills" / "setup" / "SKILL.md").exists()
        assert (tmp_path / directory / "skills" / "modern-web-guidance" / "SKILL.md").exists()
        assert (tmp_path / directory / "skills" / "system-design" / "SKILL.md").exists()
        assert (tmp_path / directory / "skills" / "draw-interaction" / "SKILL.md").exists()
        assert (tmp_path / directory / "skills" / "draw-improve" / "SKILL.md").exists()
        for level in range(1, 5):
            assert (tmp_path / directory / "skills" / f"draw-system-level-{level}" / "SKILL.md").exists()
    assert (tmp_path / ".agents/skills/draw-improve/agents/openai.yaml").exists()
    assert (tmp_path / ".agents/skills/draw-interaction/agents/openai.yaml").exists()


def test_draw_answer_skill_requires_structured_human_output_with_node_symbol():
    """Define a resposta do Draw Interaction como uma saída humana e rastreável.
    Exige que o contrato mostre o símbolo associado ao próprio nó e as evidências.
    """
    skill = Path("src/looper/templates/agents/draw-interaction/SKILL.md").read_text(encoding="utf-8")

    assert "## Formato obrigatório da resposta" in skill
    assert "### Resposta" in skill
    assert "### Nó e símbolo associado" in skill
    assert "### Evidências" in skill
    assert "### Limitações" in skill
    assert "linguagem natural" in skill
    assert "não despeje o JSON bruto" in skill
    assert "símbolo associado ao nó" in skill


def test_init_interactive_selects_multiple_agent_integrations(tmp_path: Path):
    """Permite escolher várias integrações por números durante a inicialização.
    Simula a seleção de Claude e Gemini e confirma que o setup também pode ser aceito no mesmo fluxo.
    """
    result = runner.invoke(app, ["init", str(tmp_path), "--interactive"], input="2,3\ny\n1\n1\n1\n1\n1\n")

    assert result.exit_code == 0
    assert (tmp_path / ".claude/skills/setup/SKILL.md").exists()
    assert (tmp_path / ".gemini/skills/setup/SKILL.md").exists()
    assert "Selecione" in result.stdout
    config = json.loads((tmp_path / ".looper/config.json").read_text())
    assert config["backlog"]["level_2_meaning"] == "Tela"
    assert config["backlog"]["level_3_meaning"] == "Regra de negócio"
    assert config["backlog"]["task_delivery_scope"] == "node"
    assert config["backlog"]["l2_verification_interval"] == 1


def test_init_interactive_uses_codex_without_asking_for_agent(tmp_path: Path):
    """O init interativo não abre um seletor de agentes e usa AGENTS.md como contrato comum."""
    result = runner.invoke(app, ["init", str(tmp_path), "--interactive", "--no-web"])

    assert result.exit_code == 0
    assert "Selecione as integrações" not in result.stdout
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".agents/skills/setup/SKILL.md").exists()
    assert not (tmp_path / "CLAUDE.md").exists()
    assert not (tmp_path / "GEMINI.md").exists()


def test_init_interactive_does_not_ask_frontend_analysis_policy(tmp_path: Path):
    """Inicializa projetos frontend sem abrir um gate específico.
    Confirma que o setup termina após a escolha de executar a detecção da stack.
    """
    (tmp_path / "index.html").write_text("<button>menu</button>")

    result = runner.invoke(app, ["init", str(tmp_path), "--interactive"], input="1\ny\n1\n2\n1\n1\n1\n")

    assert result.exit_code == 0
    assert "política de análise estática frontend" not in result.stdout
    config = json.loads((tmp_path / ".looper/config.json").read_text())
    assert "frontend" not in config["static_analysis"]


def test_init_interactive_accepts_custom_level_meanings(tmp_path: Path):
    """Persiste definições personalizadas para os níveis do Draw.
    Usa a opção de texto livre e mantém as definições no backlog do projeto.
    """
    result = runner.invoke(
        app,
        ["init", str(tmp_path), "--interactive"],
        input="1\ny\n2\nView pública e componentes frontend\n3\nPolíticas e detalhes de interação\n2\n1\n1\n",
    )

    assert result.exit_code == 0
    config = json.loads((tmp_path / ".looper/config.json").read_text())
    assert config["backlog"]["level_2_meaning"] == "View pública e componentes frontend"
    assert config["backlog"]["level_3_meaning"] == "Políticas e detalhes de interação"
    assert config["backlog"]["task_delivery_scope"] == "task"
    assert config["backlog"]["l2_verification_interval"] == 1


def test_init_accepts_task_delivery_scope_option(tmp_path: Path):
    """Permite configurar o agrupamento comum sem abrir o modo interativo.
    Persiste a escolha para os ciclos de teste e implementação.
    """
    result = runner.invoke(app, ["init", str(tmp_path), "--task-delivery-scope", "node"])

    assert result.exit_code == 0
    config = json.loads((tmp_path / ".looper/config.json").read_text())
    assert config["backlog"]["task_delivery_scope"] == "node"


def test_init_accepts_l2_verification_interval_option(tmp_path: Path):
    """Permite configurar pelo init a frequência da conferência dos nós L2."""
    result = runner.invoke(app, ["init", str(tmp_path), "--l2-verification-interval", "2"])

    assert result.exit_code == 0
    config = json.loads((tmp_path / ".looper/config.json").read_text())
    assert config["backlog"]["l2_verification_interval"] == 2


def test_init_can_disable_the_test_loop(tmp_path: Path):
    """Persiste a opção que entrega somente tasks de implementação.
    Confirma a configuração no arquivo do projeto.
    """
    result = runner.invoke(app, ["init", str(tmp_path), "--no-test-loop"])

    assert result.exit_code == 0
    config = json.loads((tmp_path / ".looper/config.json").read_text())
    assert config["backlog"]["test_loop_enabled"] is False


def test_init_interactive_can_disable_the_test_loop(tmp_path: Path):
    """Oferece a escolha do loop somente de implementação no init interativo.
    Confirma a escolha persistida no backlog.
    """
    result = runner.invoke(app, ["init", str(tmp_path), "--interactive"], input="1\nn\n1\n1\n2\n0\n2\n")

    assert result.exit_code == 0
    config = json.loads((tmp_path / ".looper/config.json").read_text())
    assert config["backlog"]["test_loop_enabled"] is False


def test_init_interactive_can_disable_l2_verification_tasks(tmp_path: Path):
    """Permite desabilitar as conferências automáticas durante o init interativo."""
    result = runner.invoke(app, ["init", str(tmp_path), "--interactive"], input="1\nn\n1\n1\n2\n0\n1\n")

    assert result.exit_code == 0
    config = json.loads((tmp_path / ".looper/config.json").read_text())
    assert config["backlog"]["l2_verification_interval"] == 0


def test_init_rejects_removed_frontend_analysis_option(tmp_path: Path):
    """Rejeita a opção frontend aposentada pelo CLI.
    Confirma que a análise geral continua sendo configurada sem esse gate.
    """
    result = runner.invoke(app, ["init", str(tmp_path), "--frontend-analysis", "warning"])

    assert result.exit_code != 0
    assert "frontend-analysis" in result.output


def test_init_removes_legacy_frontend_policy_without_losing_other_static_config(tmp_path: Path):
    """Migra a política frontend antiga durante a inicialização.
    Preserva adapter e quality enquanto remove somente a configuração aposentada.
    """
    init_result = runner.invoke(app, ["init", str(tmp_path)])
    assert init_result.exit_code == 0
    config_path = tmp_path / ".looper/config.json"
    config = json.loads(config_path.read_text())
    config["static_analysis"]["frontend"] = {"enabled": True, "mode": "warning"}
    config["static_analysis"]["adapter_command"] = ["python", "adapter.py"]
    config["static_analysis"]["quality"] = {"functions": {"max_lines": {"warning": 40, "blocking": 100}}}
    config_path.write_text(json.dumps(config), encoding="utf-8")

    result = runner.invoke(app, ["init", str(tmp_path)])

    assert result.exit_code == 0
    migrated = json.loads(config_path.read_text())
    assert "frontend" not in migrated["static_analysis"]
    assert migrated["static_analysis"]["adapter_command"] == ["python", "adapter.py"]
    assert migrated["static_analysis"]["quality"]["functions"]["max_lines"]["warning"] == 40


def test_setup_detects_stack_without_assuming_python(tmp_path: Path):
    """Detecta uma aplicação TypeScript e gera runner compatível com sua stack.
    Cria package.json e confirma que o diagnóstico não escolhe pytest ou outro comando Python.
    """
    (tmp_path / "package.json").write_text('{"scripts":{"test":"vitest run"},"devDependencies":{"vitest":"latest"}}')

    result = runner.invoke(app, ["setup", str(tmp_path)])

    assert result.exit_code == 0
    config = json.loads((tmp_path / ".looper/config.json").read_text())
    assert config["stack"]["languages"] == ["typescript"]
    assert config["test_commands"][0]["command"] == ["npm", "test"]
    assert "pytest" not in json.dumps(config)
    assert "dist/" in (tmp_path / ".gitignore").read_text()


def test_setup_detects_php_wordpress_and_custom_runner_and_generates_adapter(tmp_path: Path):
    """Detecta PHP e WordPress por evidências locais e configura o adapter nativo.
    Usa um runner PHP sem Composer e confirma que o setup produz comando executável.
    """
    (tmp_path / "whatsapp-plugin.php").write_text("<?php\n/** Plugin Name: Fixture */\n")
    runner_file = tmp_path / "tests/router/run.php"
    runner_file.parent.mkdir(parents=True)
    runner_file.write_text("<?php echo 'ok';\n")

    result = runner.invoke(app, ["setup", str(tmp_path)])

    assert result.exit_code == 0
    config = json.loads((tmp_path / ".looper/config.json").read_text())
    assert config["stack"]["languages"] == ["php"]
    assert "wordpress" in config["stack"]["frameworks"]
    assert "php custom runner" in config["stack"]["test_runners"]
    assert config["test_commands"][0]["command"] == ["php", "tests/router/run.php"]
    assert config["static_analysis"]["adapter_command"] == ["php", ".looper/adapters/php_static_adapter.php"]
    assert (tmp_path / ".looper/adapters/php_static_adapter.php").exists()
    assert "vendor/" in (tmp_path / ".gitignore").read_text()
    assert "._*" in (tmp_path / ".gitignore").read_text()


def test_setup_ignores_looper_php_adapter_template_when_detecting_stack(tmp_path: Path):
    """Não confunde template interno do Looper com PHP da aplicação.
    Mantém uma codebase Python identificada sem gerar adapter PHP indevido.
    """
    (tmp_path / "pyproject.toml").write_text("[project]\ndependencies = ['pytest']\n")
    template = tmp_path / "src/looper/templates/adapters/php_static_adapter.php"
    template.parent.mkdir(parents=True)
    template.write_text("<?php echo 'template';\n")

    result = runner.invoke(app, ["setup", str(tmp_path)])

    assert result.exit_code == 0
    config = json.loads((tmp_path / ".looper/config.json").read_text())
    assert config["stack"]["languages"] == ["python"]
    assert config["static_analysis"]["adapter_command"] is None
    assert not (tmp_path / ".looper/adapters/php_static_adapter.php").exists()


def test_php_adapter_reports_quality_metrics(tmp_path: Path):
    """Calcula complexidade e limites estruturais por função PHP.
    Executa o adapter gerado com um fixture controlado e valida achados determinísticos.
    """
    if shutil.which("php") is None:
        pytest.skip("PHP CLI não disponível")
    source = tmp_path / "src/Service.php"
    source.parent.mkdir()
    source.write_text(
        "<?php\nnamespace Demo;\nclass Service {\n"
        "public function process($a, $b, $c, $d, $e, $f) {\n"
        + "\n".join("if ($a) { $a = $a + 1; }" for _ in range(11))
        + "\nreturn $a;\n}\n}\n"
    )
    runner.invoke(app, ["setup", str(tmp_path)])
    request = json.dumps({"contract_version": "1", "project_path": str(tmp_path), "changed_files": [], "mode": "full"})
    process = subprocess.run(["php", ".looper/adapters/php_static_adapter.php"], cwd=tmp_path, input=request, text=True, capture_output=True)
    report = json.loads(process.stdout)

    assert process.returncode == 0
    assert report["capabilities"]["complexity"] is True
    assert any(item["qualified_name"] == "Demo\\Service::process" for item in report["symbols"])
    findings = {item["kind"] for item in report["quality_findings"]}
    assert "high_complexity" in findings
    assert "too_many_parameters" in findings


def test_php_adapter_indexes_classes_with_inheritance_and_interfaces(tmp_path: Path):
    """Indexa classes PHP mesmo quando a declaração usa extends/implements.
    Confirma a classe e mantém seus métodos qualificados pelo nome da classe.
    """
    if shutil.which("php") is None:
        pytest.skip("PHP CLI não disponível")
    source = tmp_path / "tests/ExampleTest.php"
    source.parent.mkdir(parents=True)
    source.write_text(
        "<?php\nnamespace Demo;\n"
        "final class ExampleTest extends TestCase implements Contract {\n"
        "    public function test_example() { return true; }\n"
        "}\n",
        encoding="utf-8",
    )
    runner.invoke(app, ["setup", str(tmp_path)])
    request = json.dumps({"contract_version": "1", "project_path": str(tmp_path), "changed_files": [], "mode": "full"})
    process = subprocess.run(
        ["php", ".looper/adapters/php_static_adapter.php"],
        cwd=tmp_path,
        input=request,
        text=True,
        capture_output=True,
    )
    report = json.loads(process.stdout)

    assert process.returncode == 0
    qualified_names = {item["qualified_name"] for item in report["symbols"]}
    assert "Demo\\ExampleTest" in qualified_names
    assert "Demo\\ExampleTest::test_example" in qualified_names


def test_test_runs_all_configured_suites(tmp_path: Path):
    """Executa todas as suítes de testes configuradas no alias geral do Looper.
    Cria uma configuração com duas suítes em .looper/config.json e valida o stdout do run_tests.
    """
    (tmp_path / ".looper").mkdir()
    config = {
        "test_commands": [
            {"name": "unit", "command": [sys.executable, "-c", "print('unit')"]},
            {"name": "integration", "command": [sys.executable, "-c", "print('integration')"]},
        ]
    }
    (tmp_path / ".looper/config.json").write_text(json.dumps(config))
    process, report = run_tests(tmp_path)
    assert process.returncode == 0
    assert report["status"] == "passed"
    assert "[unit]" in process.stdout
    assert "[integration]" in process.stdout
    assert report["summary"] == {"total": 2, "passed": 2, "failed": 0, "not_executed": 0}
    assert [suite["name"] for suite in report["suites"]] == ["unit", "integration"]


def test_playwright_suite_is_opt_in_and_regression_runs_by_default(tmp_path: Path):
    """Mantém Playwright fora do alias padrão sem pular a regressão da codebase."""
    (tmp_path / ".looper").mkdir()
    config = {
        "test_commands": [
            {"name": "regression", "command": [sys.executable, "-c", "print('regression-ran')"]},
            {"name": "browser", "type": "playwright", "command": [sys.executable, "-c", "print('playwright-ran')"]},
        ]
    }
    (tmp_path / ".looper/config.json").write_text(json.dumps(config))

    default_process, default_report = run_tests(tmp_path)
    playwright_process, playwright_report = run_tests(tmp_path, include_playwright=True)

    assert default_process.returncode == 0
    assert "regression-ran" in default_process.stdout
    assert "playwright-ran" not in default_process.stdout
    assert [(suite["name"], suite["status"], suite.get("reason")) for suite in default_report["suites"]] == [
        ("regression", "passed", None),
        ("browser", "not_executed", "playwright_opt_in_required"),
    ]
    assert playwright_process.returncode == 0
    assert "playwright-ran" in playwright_process.stdout
    assert playwright_report["summary"]["passed"] == 2


def test_test_cli_exposes_playwright_opt_in_flag(tmp_path: Path, monkeypatch):
    """A flag pública libera somente a execução Playwright solicitada."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".looper").mkdir()
    config = {
        "test_commands": [{"name": "browser", "type": "playwright", "command": [sys.executable, "-c", "print('browser-ran')"]}]
    }
    (tmp_path / ".looper/config.json").write_text(json.dumps(config))

    default = runner.invoke(app, ["test"])
    opted_in = runner.invoke(app, ["test", "--playwright"])

    assert default.exit_code == 0
    assert "playwright_opt_in_required" in default.stdout
    assert "browser-ran" not in default.stdout
    assert opted_in.exit_code == 0
    assert "browser-ran" in opted_in.stdout


def test_global_test_alias_continues_after_suite_failure(tmp_path: Path):
    """Executa todas as suítes mesmo quando uma delas falha no alias global.
    Configura uma falha antes de uma suíte válida e confirma o relatório consolidado das duas.
    """
    (tmp_path / ".looper").mkdir()
    config = {
        "test_commands": [
            {"name": "database", "command": [sys.executable, "-c", "raise SystemExit(3)"]},
            {"name": "security", "command": [sys.executable, "-c", "print('security-ran')"]},
        ]
    }
    (tmp_path / ".looper/config.json").write_text(json.dumps(config))

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
    (tmp_path / ".looper").mkdir()
    config = {
        "testing": {"profile": "mvp"},
        "test_commands": [
            {"name": "unit", "command": [sys.executable, "-c", "print('unit')"], "profiles": ["mvp"]},
            {"name": "database", "command": [sys.executable, "-c", "raise SystemExit(9)"], "requires_approval": True},
            {"name": "performance", "command": [sys.executable, "-c", "raise SystemExit(9)"], "enabled": False},
        ],
    }
    (tmp_path / ".looper/config.json").write_text(json.dumps(config))

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
    (tmp_path / ".looper").mkdir()
    config = {
        "testing": {"profile": "mvp"},
        "test_commands": [
            {"name": "unit", "command": [sys.executable, "-c", "print('unit')"]},
            {"name": "database", "command": [sys.executable, "-c", "print('database')"], "requires_approval": True},
        ],
    }
    (tmp_path / ".looper/config.json").write_text(json.dumps(config))

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
    (tmp_path / ".looper").mkdir()
    config = {
        "test_commands": [
            {"name": "database", "command": [sys.executable, "-c", "print('database-executed')"], "requires_approval": True}
        ]
    }
    (tmp_path / ".looper/config.json").write_text(json.dumps(config))

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
    (tmp_path / ".looper").mkdir()
    config = {
        "test_commands": [{"name": "unit", "command": [sys.executable, "-c", "print('unit')"]}],
        "static_analysis": {"enabled": True, "adapter_command": None, "contract_version": "1"},
    }
    (tmp_path / ".looper/config.json").write_text(json.dumps(config))

    process, report = run_tests(tmp_path)

    assert process.returncode == 0
    assert report["status"] == "passed"
    assert report["static_analysis"]["status"] == "unavailable"
    assert report["static_analysis"]["reason"] == "adapter_not_configured"
    assert "[static-analysis]" in process.stdout


def test_test_cli_blocks_draw_node_without_associated_symbol(tmp_path: Path, monkeypatch):
    """Bloqueia o CLI quando um nó de jornada não possui símbolo associado.
    Executa `looper test` e confirma o finding determinístico da análise dos Draws.
    """
    monkeypatch.chdir(tmp_path)
    draws = tmp_path / ".looper" / "draws"
    draws.mkdir(parents=True)
    (draws / "journey.json").write_text(json.dumps({
        "id": "journey",
        "title": "Jornada sem símbolo",
        "hierarchy": {"level": 2, "role": "journey", "root_draw_ref": "root"},
        "nodes": [{"id": 1, "label": "Tela sem referência"}],
        "edges": [],
    }), encoding="utf-8")
    (tmp_path / ".looper" / "config.json").write_text(json.dumps({
        "test_commands": [{"name": "unit", "command": [sys.executable, "-c", "print('unit')"]}],
        "static_analysis": {"enabled": True, "adapter_command": None},
    }), encoding="utf-8")
    (tmp_path / ".looper" / "backlog.json").write_text(json.dumps({"tasks": [{
        "id": "task:journey:node:1", "draw_id": "journey", "node_id": 1,
        "status": "done", "checklist_state": {"implementation": True},
    }]}), encoding="utf-8")

    result = runner.invoke(app, ["test"])

    assert result.exit_code != 0
    report = yaml.safe_load(result.output)
    assert report["status"] == "blocked"
    assert report["checks"]["draws"]["status"] == "blocked"
    issue = report["checks"]["draws"]["issues"][0]
    assert issue["draw"] == "journey"
    assert issue["title"] == "Jornada sem símbolo"
    assert issue["node"] == 1
    assert issue["node_label"] == "Tela sem referência"
    assert issue["rule"] == "draw.level2_missing_code_ref"


def test_draw_symbols_lists_missing_nodes_without_running_test_suites(tmp_path: Path, monkeypatch):
    """Lista símbolos e detecta nós sem associação no comando dedicado.
    Configura uma suíte que deixaria marcador e confirma que ela não é executada.
    """
    monkeypatch.chdir(tmp_path)
    draws = tmp_path / ".looper" / "draws"
    draws.mkdir(parents=True)
    (draws / "journey.json").write_text(json.dumps({
        "id": "journey",
        "title": "Jornada com símbolos",
        "hierarchy": {"level": 2, "role": "journey", "root_draw_ref": "root"},
        "nodes": [
            {"id": 1, "label": "Associado", "code_refs": [{"symbol": "journey.start"}]},
            {"id": 2, "label": "Sem símbolo"},
        ],
        "edges": [],
    }), encoding="utf-8")
    (tmp_path / ".looper" / "config.json").write_text(json.dumps({
        "test_commands": [{
            "name": "must-not-run",
            "command": [sys.executable, "-c", "from pathlib import Path; Path('suite-ran').write_text('x')"],
        }],
    }), encoding="utf-8")

    result = runner.invoke(app, ["draw", "symbols"])

    report = json.loads(result.stdout)
    assert result.exit_code == 0
    assert report["status"] == "passed"
    assert report["summary"] == {"nodes": 2, "associated": 1, "missing": 1, "draws": 1}
    assert report["draws"][0]["symbols"] == ["journey.start"]
    assert report["draws"][1]["status"] == "missing"
    assert not (tmp_path / "suite-ran").exists()


def test_test_compacts_static_analysis_output_but_preserves_structured_report(tmp_path: Path):
    """Resume a saída textual sem perder o relatório estruturado da análise.
    Emite muitos símbolos no adapter e confirma que o terminal não recebe o dump completo.
    """
    (tmp_path / ".looper").mkdir()
    adapter_result = {
        "contract_version": "1",
        "status": "passed",
        "capabilities": {"symbols": True},
        "symbols": [{"qualified_name": f"module.Symbol{index}"} for index in range(300)],
        "dependencies": [],
        "complexity": [],
        "structural_metrics": [],
        "quality_findings": [],
        "changes": [],
        "warnings": [],
        "errors": [],
    }
    adapter_code = "import json; print(json.dumps(" + repr(adapter_result) + "))"
    config = {
        "test_commands": [{"name": "unit", "command": [sys.executable, "-c", "print('unit')"]}],
        "static_analysis": {"adapter_command": [sys.executable, "-c", adapter_code]},
    }
    (tmp_path / ".looper/config.json").write_text(json.dumps(config))

    process, report = run_tests(tmp_path)

    assert process.returncode == 0
    assert len(report["static_analysis"]["symbols"]) == 300
    assert "module.Symbol299" not in process.stdout
    assert '"symbols": 300' in process.stdout


def test_test_executes_fake_static_analysis_adapter(tmp_path: Path):
    """Executa um adaptador fake e incorpora seu relatório factual ao resultado do teste.
    Configura um comando Python que retorna dependências e complexidade em JSON válido.
    """
    (tmp_path / ".looper").mkdir()
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
    (tmp_path / ".looper/config.json").write_text(json.dumps(config))

    process, report = run_tests(tmp_path)

    assert process.returncode == 0
    assert report["static_analysis"]["status"] == "passed"
    assert report["static_analysis"]["dependencies"][0]["target"] == "os"
    assert report["static_analysis"]["complexity"][0]["cyclomatic"] == 3


def test_test_blocks_invalid_static_analysis_output(tmp_path: Path):
    """Bloqueia a execução quando o adaptador não cumpre o schema agnóstico.
    Configura um adaptador que retorna um objeto incompleto e verifica o motivo estruturado.
    """
    (tmp_path / ".looper").mkdir()
    config = {
        "test_commands": [{"name": "unit", "command": [sys.executable, "-c", "print('unit')"]}],
        "static_analysis": {"adapter_command": [sys.executable, "-c", "print('{}')"]},
    }
    (tmp_path / ".looper/config.json").write_text(json.dumps(config))

    process, report = run_tests(tmp_path)

    assert process.returncode != 0
    assert report["status"] == "blocked"
    assert report["static_analysis"]["status"] == "blocked"
    assert report["static_analysis"]["reason"] == "adapter_schema_invalid"


def test_test_blocks_blocking_long_function_quality_finding(tmp_path: Path):
    """Bloqueia uma função acima do limite configurado quando o adaptador reporta severidade blocking.
    Retorna um achado long_function válido e verifica que o gate impede a aprovação silenciosa.
    """
    (tmp_path / ".looper").mkdir()
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
    (tmp_path / ".looper/config.json").write_text(json.dumps(config))

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
    Invoca looper log e confirma a presença de somente um arquivo de cada tipo.
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["log", "Adiciona nova feature com testes", "-i", "-t"])
    assert result.exit_code == 0
    assert "Registro gravado em" in result.stdout

    day_folders = [p for p in (tmp_path / ".looper/runs").iterdir() if p.is_dir() and p.name != "data"]
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
    assert not (tmp_path / ".looper/latest_snapshot.json").exists()
    assert not (tmp_path / ".looper/runs/data/latest_snapshot.json").exists()


def test_log_ignores_invalid_utf8_appledouble_snapshot(tmp_path: Path, monkeypatch):
    """Mantém o log funcionando quando o macOS deixa snapshot AppleDouble inválido.
    Cria um arquivo ._ binário no histórico e confirma que o próximo log não falha ao ler o diff.
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    first = runner.invoke(app, ["log", "Primeiro registro", "-i"])
    assert first.exit_code == 0
    day_folder = next(path for path in (tmp_path / ".looper/runs").iterdir() if path.is_dir() and path.name != "data")
    (day_folder / "._invalid_snapshot.json").write_bytes(b"AppleDouble\x00\xff")

    second = runner.invoke(app, ["log", "Segundo registro", "-t"])

    assert second.exit_code == 0
    assert "Registro gravado em" in second.stdout


def test_workspace_snapshot_excludes_looper_draw_and_run_json_documents(tmp_path: Path):
    """Exclui JSONs operacionais dos desenhos e das execuções.
    Mantém arquivos de código do projeto disponíveis para o diff incremental.
    """
    (tmp_path / ".looper/draws").mkdir(parents=True)
    (tmp_path / ".looper/runs/2026-08-03").mkdir(parents=True)
    (tmp_path / ".looper/draws/subfluxo.json").write_text('{"nodes": []}', encoding="utf-8")
    (tmp_path / ".looper/runs/2026-08-03/2026-08-03_summary.json").write_text('{"runs": []}', encoding="utf-8")
    source = tmp_path / "feature.py"
    source.write_text("value = 1\n", encoding="utf-8")

    snapshot = get_workspace_snapshot(tmp_path)

    assert "feature.py" in snapshot
    assert all(not path.startswith(".looper/") for path in snapshot)


def test_workspace_snapshot_respects_gitignore_exceptions_in_git_checkout(tmp_path: Path):
    """Mantém arquivos liberados por exceções após um padrão global ``*``."""
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, text=True, check=True)
    (tmp_path / ".gitignore").write_text(
        "*\n"
        "!.looper/\n"
        "!.looper/**\n"
        "!wp-content/\n"
        "!wp-content/plugins/\n"
        "!wp-content/plugins/example/\n"
        "!wp-content/plugins/example/**\n",
        encoding="utf-8",
    )
    plugin_file = tmp_path / "wp-content/plugins/example/example.php"
    plugin_file.parent.mkdir(parents=True)
    plugin_file.write_text("<?php\nreturn true;\n", encoding="utf-8")
    (tmp_path / "outside.php").write_text("<?php\nreturn false;\n", encoding="utf-8")

    snapshot = get_workspace_snapshot(tmp_path)

    assert "wp-content/plugins/example/example.php" in snapshot
    assert "outside.php" not in snapshot


def test_runs_apply_current_gitignore_to_previous_snapshot_in_real_time(tmp_path: Path, monkeypatch):
    """Não transforma mudanças no gitignore em falso delete ou falso restore."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    tracked = tmp_path / "temporary.py"
    tracked.write_text("value = 1\n", encoding="utf-8")
    first = runner.invoke(app, ["log", "Registra arquivo", "-i"])
    assert first.exit_code == 0

    gitignore = tmp_path / ".gitignore"
    gitignore.write_text(gitignore.read_text(encoding="utf-8") + "\ntemporary.py\n", encoding="utf-8")
    tracked.write_text("value = 2\n", encoding="utf-8")
    second = runner.invoke(app, ["log", "Passa a ignorar arquivo", "-i"])
    assert second.exit_code == 0
    day_folder = next(path for path in (tmp_path / ".looper/runs").iterdir() if path.is_dir() and path.name != "data")
    snapshot = json.loads((day_folder / f"{day_folder.name}_snapshot.json").read_text(encoding="utf-8"))
    assert all(file["path"] != "temporary.py" for file in snapshot["runs"][-1]["files"])

    gitignore.write_text(gitignore.read_text(encoding="utf-8").replace("\ntemporary.py\n", "\n"), encoding="utf-8")
    tracked.write_text("value = 3\n", encoding="utf-8")
    third = runner.invoke(app, ["log", "Volta a observar arquivo", "-i"])
    assert third.exit_code == 0
    snapshot = json.loads((day_folder / f"{day_folder.name}_snapshot.json").read_text(encoding="utf-8"))
    assert any(file["path"] == "temporary.py" for file in snapshot["runs"][-1]["files"])


def test_log_accumulates_runs_in_one_summary_and_snapshot_per_day(tmp_path: Path, monkeypatch):
    """Mantém somente um summary e um snapshot e acumula as duas execuções.
    Executa dois registros no mesmo dia e verifica que os relatórios preservam ambos os run_id.
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])

    first = runner.invoke(app, ["log", "Primeiro registro", "-i"])
    day_folder = next(path for path in (tmp_path / ".looper/runs").iterdir() if path.is_dir() and path.name != "data")
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
    assert not (tmp_path / ".looper/latest_snapshot.json").exists()
    assert not (tmp_path / ".looper/runs/data/latest_snapshot.json").exists()


def test_log_migrates_legacy_daily_documents_before_appending(tmp_path: Path, monkeypatch):
    """Converte o formato diário antigo para a lista incremental sem perder a execução anterior.
    Cria documentos legados e confirma que o novo registro preserva ambos os run_id.
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    day_folder = tmp_path / ".looper/runs" / day
    day_folder.mkdir(parents=True)
    (day_folder / f"{day}_summary.json").write_text(
        json.dumps({"run_id": "legacy-summary", "timestamp": f"{day}T10:00:00+00:00", "description": "Legado", "work_types": ["teste"], "diff_stats": {}}),
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
    day_folder = next(path for path in (tmp_path / ".looper/runs").iterdir() if path.is_dir() and path.name != "data")
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
    """Respeita as extensões rastreadas customizadas no arquivo .looper/config.json.
    Adiciona .md às extensões rastreadas, modifica um arquivo markdown e valida no snapshot.
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    config_path = tmp_path / ".looper/config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["tracked_extensions"] = [".py", ".md"]
    config_path.write_text(json.dumps(config), encoding="utf-8")

    doc_file = tmp_path / "doc.md"
    doc_file.write_text("# Especificação\nLinha 1\n")

    result = runner.invoke(app, ["log", "Atualiza documentação markdown", "-i"])
    assert result.exit_code == 0

    day_folder = next(path for path in (tmp_path / ".looper/runs").iterdir() if path.is_dir() and path.name != "data")
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
    day_folder = next(path for path in (tmp_path / ".looper/runs").iterdir() if path.is_dir() and path.name != "data")
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
    day_folder = next(path for path in (tmp_path / ".looper/runs").iterdir() if path.is_dir() and path.name != "data")
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
    """Rejeita comandos looper log sem informar nenhum tipo de trabalho.
    Invoca looper log sem flags -i, -t, -b ou -r e valida a mensagem de erro.
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["log", "Descrição sem tipo"])
    assert result.exit_code != 0
    assert "Ao menos um tipo de trabalho deve ser informado" in result.stderr


def test_draw_diff_command_reads_only_logged_draw_json_changes(tmp_path: Path, monkeypatch):
    """Exibe somente mudanças de JSONs de Draws registradas por log.
    Ignora alterações simultâneas em arquivos de código e o índice operacional.
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    draws_dir = tmp_path / ".looper/draws"
    draw_file = draws_dir / "checkout.json"
    draw_file.write_text('{"id":"checkout","title":"Inicial"}\n', encoding="utf-8")
    (tmp_path / "service.py").write_text("return 1\n", encoding="utf-8")
    first = runner.invoke(app, ["log", "Baseline do desenho", "-i"])
    assert first.exit_code == 0

    draw_file.write_text('{"id":"checkout","title":"Atualizado"}\n', encoding="utf-8")
    (tmp_path / "service.py").write_text("return 2\n", encoding="utf-8")
    result = runner.invoke(app, ["draw", "diff"])

    assert result.exit_code == 0
    assert "checkout.json" in result.stdout
    assert "Atualizado" in result.stdout
    assert "service.py" not in result.stdout
    assert "index.json" not in result.stdout

    second = runner.invoke(app, ["log", "Atualiza desenho", "-i"])
    assert second.exit_code == 0
    after_log = runner.invoke(app, ["draw", "diff"])
    assert after_log.exit_code == 0
    assert "Nenhuma alteração nos JSONs de Draws desde o último log." in after_log.stdout


def test_log_marks_draw_only_changes_as_zero_line_checkpoint(tmp_path: Path, monkeypatch):
    """Marca alterações apenas no Draw como checkpoints sem linhas de código.
    Mantém o diff incremental dos JSONs disponível no snapshot da run.
    """
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    draw_file = tmp_path / ".looper/draws/checkout.json"
    draw_file.write_text('{"title":"Inicial"}\n', encoding="utf-8")
    baseline = runner.invoke(app, ["log", "Baseline do desenho", "-i"])
    assert baseline.exit_code == 0

    draw_file.write_text('{"title":"Atualizado"}\n', encoding="utf-8")
    result = runner.invoke(app, ["log", "Atualiza desenho", "-i"])
    assert result.exit_code == 0

    summary_file = next((tmp_path / ".looper/runs").glob("*/*_summary.json"))
    latest = json.loads(summary_file.read_text(encoding="utf-8"))["runs"][-1]

    assert latest["checkpoint"] is True
    assert latest["diff_stats"]["lines_added"] == 0
    assert latest["diff_stats"]["lines_deleted"] == 0
    assert latest["draw_diff_stats"]["files_changed"] == 1


def test_init_configures_all_backlog_options_via_cli(tmp_path: Path):
    """Inicializa projeto com todas as opções de backlog e valida config.json."""
    result = runner.invoke(
        app,
        [
            "init",
            str(tmp_path),
            "--development-mode",
            "separated",
            "--verification-interval",
            "4",
            "--task-batch-size",
            "3",
            "--task-batch-scope",
            "task",
            "--bootstrap",
            "--final-verification",
            "--min-task-interval-seconds",
            "10",
        ],
    )
    assert result.exit_code == 0
    config = json.loads((tmp_path / ".looper/config.json").read_text(encoding="utf-8"))["backlog"]
    assert config["development_mode"] == "separated"
    assert config["verification_interval"] == 4
    assert config["task_batch_size"] == 3
    assert config["task_batch_scope"] == "task"
    assert config["bootstrap_task"] is True
    assert config["final_verification_task"] is True
    assert config["min_task_interval_seconds"] == 10


def test_cli_backlog_frontend_and_backend_subcommands(tmp_path: Path, monkeypatch):
    """Executa os subcomandos looper backlog frontend e looper backlog backend."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(
        app,
        [
            "init",
            "--development-mode",
            "separated",
            "--no-bootstrap",
            "--no-test-loop",
        ],
    )
    from looper.draw import create_draw
    create_draw(
        tmp_path,
        {
            "id": "sistema",
            "title": "Sistema",
            "kind": "system",
            "hierarchy": {"level": 1, "role": "architecture", "root_draw_ref": "sistema"},
            "groups": [],
            "nodes": [
                {"id": 1, "label": "Jornada", "description": "Jornada principal.", "draw_ref": "jornada"},
                {"id": 2, "label": "Fim", "description": "Fim do fluxo."},
            ],
            "edges": [{"id": 1, "from": 1, "to": 2, "kind": "flow", "condition": 1}],
            "flows": [],
        },
    )
    create_draw(
        tmp_path,
        {
            "id": "jornada",
            "title": "Jornada do usuário",
            "kind": "flow",
            "hierarchy": {
                "level": 2,
                "role": "journey",
                "parent_draw_ref": "sistema",
                "parent_node_id": 1,
                "root_draw_ref": "sistema",
            },
            "groups": [],
            "nodes": [
                {"id": 1, "label": "Tela Principal", "description": "Tela da home.", "draw_ref": "subjornada"},
                {"id": 2, "label": "Tela Conclusão", "description": "Conclusão."},
            ],
            "edges": [{"id": 1, "from": 1, "to": 2, "kind": "flow", "condition": 1}],
            "flows": [],
        },
    )
    create_draw(
        tmp_path,
        {
            "id": "subjornada",
            "title": "Subjornada interna",
            "kind": "flow",
            "hierarchy": {
                "level": 3,
                "role": "implementation",
                "parent_draw_ref": "jornada",
                "parent_node_id": 1,
                "root_draw_ref": "sistema",
            },
            "groups": [],
            "nodes": [
                {"id": 1, "label": "Processar Dados", "description": "Processa dados no backend."},
                {"id": 2, "label": "Finalizar Processamento", "description": "Finaliza backend."},
            ],
            "edges": [{"id": 1, "from": 1, "to": 2, "kind": "flow", "condition": 1}],
            "flows": [],
        },
    )

    front = runner.invoke(app, ["backlog", "frontend"])
    assert front.exit_code == 0
    assert "Tela Principal" in front.stdout
    assert "frontend" in front.stdout.lower()

    from looper.backlog import complete_backlog_task
    complete_backlog_task(tmp_path, "task:jornada:node:1")

    back = runner.invoke(app, ["backlog", "backend"])
    assert back.exit_code == 0
    assert "Processar Dados" in back.stdout
    assert "Tela pai correspondente (L2):" in back.stdout
    assert "Tela Principal" in back.stdout
