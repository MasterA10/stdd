import json
from pathlib import Path

from typer.testing import CliRunner

from stdd.cli import app
from stdd.core import agent_templates, init_project


runner = CliRunner()


def test_init_is_idempotent_and_installs_codex_agents(tmp_path: Path, monkeypatch):
    """Inicializa a estrutura do projeto e garante idempotência no comando init.
    Executa stdd init duas vezes e valida se config.json e skills são criados sem erros.
    """
    monkeypatch.chdir(tmp_path)
    first = runner.invoke(app, ["init"])
    second = runner.invoke(app, ["init"])
    assert first.exit_code == 0
    assert second.exit_code == 0
    assert (tmp_path / ".stdd/config.json").exists()
    assert (tmp_path / ".agents/skills/feature/SKILL.md").exists()
    assert (tmp_path / ".agents/skills/implement/SKILL.md").exists()
    assert (tmp_path / ".agents/skills/setup/SKILL.md").exists()
    assert (tmp_path / ".agents/skills/static-analysis/SKILL.md").exists()
    assert (tmp_path / ".agents/skills/draw-feature/SKILL.md").exists()
    assert "testes" in (tmp_path / ".agents/skills/feature/SKILL.md").read_text().lower()
    for source in agent_templates():
        installed = tmp_path / ".agents" / "skills" / source.parent.name / "SKILL.md"
        assert installed.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")


def test_init_defers_language_specific_test_runner_to_setup(tmp_path: Path):
    """Mantém o init agnóstico e não escolhe um runner de linguagem antecipadamente.
    Chama init_project e verifica que a configuração inicial aguarda o setup da stack.
    """
    init_project(tmp_path)
    config = json.loads((tmp_path / ".stdd/config.json").read_text())
    assert config["test_commands"] == []
    assert config["testing"]["profile"] == "mvp"


def test_init_accepts_project_directory_argument(tmp_path: Path, monkeypatch):
    """Inicializa um projeto novo no diretório informado pelo usuário.
    Executa init com caminho relativo a outro diretório e confirma os artefatos no alvo.
    """
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "my-project"])

    assert result.exit_code == 0
    assert (tmp_path / "my-project/.stdd/config.json").exists()
    assert (tmp_path / "my-project/.agents/skills/feature/SKILL.md").exists()
    assert not (tmp_path / ".stdd").exists()


def test_init_rejects_file_as_project_directory(tmp_path: Path):
    """Rejeita um arquivo como destino de inicialização do projeto.
    Cria um arquivo e confirma que init falha sem escrever ao lado dele.
    """
    target = tmp_path / "not-a-directory"
    target.write_text("existing")

    result = runner.invoke(app, ["init", str(target)])

    assert result.exit_code == 1
    assert "diretório" in result.output.lower()


def test_init_keeps_framework_artifacts_in_stdd_and_agent_skills_in_agents(tmp_path: Path):
    """Mantém artefatos do framework em .stdd e skills de agentes em .agents/skills.
    Inicializa um projeto vazio e verifica que nenhum outro diretório ou arquivo é criado na raiz.
    """
    init_project(tmp_path)

    assert {path.name for path in tmp_path.iterdir()} == {".stdd", ".agents", ".gitignore"}
    assert (tmp_path / ".agents/skills/feature/SKILL.md").exists()
    assert (tmp_path / ".agents/skills/implement/SKILL.md").exists()
    assert (tmp_path / ".agents/skills/setup/SKILL.md").exists()
    assert not (tmp_path / ".agents/config.json").exists()
    assert (tmp_path / ".stdd/config.json").exists()
    assert (tmp_path / ".stdd/draw.html").exists()
    assert (tmp_path / ".stdd/draws/index.json").exists()
    assert (tmp_path / ".stdd/runs.html").exists()
    assert (tmp_path / ".stdd/runs/index.json").exists()
    gitignore = (tmp_path / ".gitignore").read_text()
    assert ".env" in gitignore
    assert "*.pyc" in gitignore
    assert "__pycache__/" in gitignore
    assert ".cache/" in gitignore
    assert "*.cache" in gitignore
    assert ".coverage" in gitignore


def test_init_preserves_existing_gitignore_and_does_not_duplicate_rules(tmp_path: Path):
    """Completa o gitignore existente sem apagar regras ou duplicar padrões STDD.
    Inicializa duas vezes um projeto com regra própria e conta uma ocorrência de cada padrão gerenciado.
    """
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("# regra do projeto\n*.log\n")

    init_project(tmp_path)
    init_project(tmp_path)

    content = gitignore.read_text()
    assert "# regra do projeto" in content
    assert "*.log" in content
    assert content.count(".env\n") == 1
    assert content.count("*.pyc\n") == 1


def test_agents_are_loaded_from_markdown_templates():
    """Carrega as skills dos agentes a partir dos templates de arquivos SKILL.md.
    Chama agent_templates e valida a presença dos títulos dos agentes feature, implement e setup.
    """
    templates = {template.parent.name: template for template in agent_templates()}
    assert set(templates) == {"draw-feature", "feature", "implement", "setup", "static-analysis"}
    assert "# Feature Agent" in templates["feature"].read_text()
    assert "# Implement Agent" in templates["implement"].read_text()
    assert "# Setup Agent" in templates["setup"].read_text()
    assert "complexidade ciclomática" in templates["static-analysis"].read_text()
    assert "long_function" in templates["static-analysis"].read_text()
    assert "acima de 100" in templates["static-analysis"].read_text()
    assert "Classe Deus" in templates["static-analysis"].read_text()
    assert "Etapa 1" in templates["static-analysis"].read_text()
    assert "hardcoded_secret" in templates["static-analysis"].read_text()
    assert "[REDACTED]" in templates["static-analysis"].read_text()
    assert ".env" in templates["static-analysis"].read_text()
    assert "*.pyc" in templates["static-analysis"].read_text()
    assert "stdd draw create" in templates["draw-feature"].read_text()


def test_agent_skills_are_self_contained_and_do_not_reference_internal_plan():
    """Exige frontmatter canônico e remove dependência do backlog interno das skills.
    Percorre todos os templates e valida metadados mínimos e autonomia das instruções.
    """
    templates = agent_templates()

    for template in templates:
        content = template.read_text(encoding="utf-8")
        assert content.startswith("---\nname:")
        assert "\ndescription:" in content.split("---", 2)[1]
        assert "general-plan" not in content.lower()


def test_delivery_agents_define_complete_production_test_contract():
    """Exige que setup, feature e implement cubram testes funcionais e não funcionais.
    Valida contratos para IA real, banco, desempenho, segurança, isolamento e pentest.
    """
    templates = {template.parent.name: template.read_text(encoding="utf-8").lower() for template in agent_templates()}

    for name in ("setup", "feature", "implement"):
        content = templates[name]
        for required in ("teste live", "pgtap", "performance", "segurança", "isolamento", "pentest", "not_executed"):
            assert required in content, f"{name} não define {required}"


def test_feature_skill_uses_tests_and_draw_json_without_markdown_copies():
    """Mantém testes e desenhos como fontes diretas da especificação da feature.
    Impede que a skill volte a criar request.md ou scenarios.md como cópias intermediárias.
    """
    content = (Path("src/stdd/templates/agents/feature/SKILL.md")).read_text(encoding="utf-8")

    assert ".stdd/draws/<draw-id>.json" in content
    assert "request.md" not in content
    assert "scenarios.md" not in content


def test_setup_skill_defines_global_alias_and_database_lifecycle():
    """Exige um alias global que inclua runners com preparação e limpeza de banco.
    Valida que falhas não interrompem as suítes seguintes e aparecem no resultado consolidado.
    """
    content = Path("src/stdd/templates/agents/setup/SKILL.md").read_text(encoding="utf-8").lower()

    for required in ("alias global", "todas as suítes", "migrations", "cleanup", "não interrompe"):
        assert required in content


def test_agent_skills_require_approval_for_expensive_or_mutating_setup():
    """Impede instalação, download e provisionamento sem autorização do usuário.
    Confirma que setup e implement preservam controle explícito em perfis flexíveis como MVP.
    """
    for name in ("setup", "implement"):
        content = Path(f"src/stdd/templates/agents/{name}/SKILL.md").read_text(encoding="utf-8").lower()
        for required in ("mvp", "aprovação explícita", "instalar", "baixar", "container", "criar banco"):
            assert required in content, f"{name} não define {required}"


def test_init_does_not_create_feature_or_implementation_commands():
    """Garante que a CLI pública do STDD expõe unicamente init e test.
    Invoca stdd --help e assegura que feature e implement não constam na lista de comandos.
    """
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "init" in result.stdout
    assert "test" in result.stdout
    assert "feature" not in result.stdout
    assert "implement" not in result.stdout


def test_runs_viewer_is_read_only_and_uses_incremental_json_documents():
    """Mantém o viewer de runs restrito à leitura dos índices e relatórios JSON.
    Confirma que o template não contém comandos de gravação ou endpoints de alteração.
    """
    template = Path("src/stdd/templates/runs/runs.html").read_text(encoding="utf-8")

    assert "fetch('runs/index.json')" in template
    assert "fetch(`runs/${day.summary}`)" in template
    assert "fetch(`runs/${day.snapshot}`)" in template
    assert "Somente leitura" in template
    assert "method: 'PUT'" not in template
    assert "method: 'POST'" not in template
    assert "method: 'DELETE'" not in template
    assert "writeText" not in template
