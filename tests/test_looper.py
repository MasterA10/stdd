import json
import subprocess
import sys
from pathlib import Path

from typer.testing import CliRunner

from looper.cli import app
from looper.core import agent_templates, init_project


runner = CliRunner()


def test_init_is_idempotent_and_installs_codex_agents(tmp_path: Path, monkeypatch):
    """Inicializa a estrutura do projeto e garante idempotência no comando init.
    Executa looper init duas vezes e valida se config.yaml e skills são criados sem erros.
    """
    monkeypatch.chdir(tmp_path)
    first = runner.invoke(app, ["init"])
    second = runner.invoke(app, ["init"])
    assert first.exit_code == 0
    assert second.exit_code == 0
    assert (tmp_path / ".looper/config.yaml").exists()
    assert (tmp_path / ".agents/skills/test-application/SKILL.md").exists()
    assert (tmp_path / ".agents/conventions/README.md").exists()
    assert sorted(path.name for path in (tmp_path / ".agents/conventions").glob("*.md")) == ["README.md"]
    conventions = (tmp_path / ".agents/conventions/README.md").read_text(encoding="utf-8")
    assert "orientação técnica específica" in conventions
    assert "contratos de APIs/apps externos" in conventions
    assert "regras de negócio" in conventions
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "somente para visão geral, operação, escopo e rastreabilidade" in agents
    assert "registre o contrato no `AGENTS.md`" not in agents
    assert not (tmp_path / ".agents/skills/create-tests-backlog").exists()
    assert not (tmp_path / ".agents/skills/e2e-tester").exists()
    assert not (tmp_path / ".agents/skills/feature").exists()
    assert not (tmp_path / ".agents/skills/implement-backlog").exists()
    assert (tmp_path / ".agents/skills/implement-frontend/SKILL.md").exists()
    assert (tmp_path / ".agents/skills/implement-backend/SKILL.md").exists()
    assert (tmp_path / ".agents/skills/setup/SKILL.md").exists()
    assert (tmp_path / ".agents/skills/static-analysis/SKILL.md").exists()
    assert (tmp_path / ".agents/skills/modern-web-guidance/SKILL.md").exists()
    assert (tmp_path / ".agents/skills/system-design/SKILL.md").exists()
    assert (tmp_path / ".agents/skills/draw-feature/SKILL.md").exists()
    assert (tmp_path / ".agents/skills/draw-improve/SKILL.md").exists()
    assert (tmp_path / ".agents/skills/draw-interaction/SKILL.md").exists()
    assert (tmp_path / ".agents/skills/implement-change/SKILL.md").exists()
    planned_level_two = (tmp_path / ".agents/skills/draw-system-level-2/SKILL.md").read_text(encoding="utf-8").lower()
    planned_level_three = (tmp_path / ".agents/skills/draw-system-level-3/SKILL.md").read_text(encoding="utf-8").lower()
    assert "subfluxo pode ser gerado sem código" in planned_level_two
    assert "pode ser criado antes da implementação" in planned_level_three
    assert "nunca crie um símbolo placeholder" in planned_level_three
    assert not (tmp_path / ".agents/skills/missing/SKILL.md").exists()
    for level in range(1, 5):
        assert (tmp_path / ".agents/skills" / f"draw-system-level-{level}" / "SKILL.md").exists()
        assert (tmp_path / ".agents/skills" / f"draw-system-level-{level}" / "agents/openai.yaml").exists()
    assert (tmp_path / ".agents/skills/draw-improve/agents/openai.yaml").exists()
    assert (tmp_path / "AGENTS.md").exists()
    assert "looper test" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "$modern-web-guidance" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "subagentes" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "tmux" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    system_design = (tmp_path / ".agents/skills/system-design/SKILL.md").read_text(encoding="utf-8")
    assert "design system" in system_design
    assert "`.looper/design.html`" in system_design
    assert "playwright-cli" in (tmp_path / ".agents/skills/test-application/SKILL.md").read_text().lower()
    assert not (tmp_path / ".agents/skills/create-tests/SKILL.md").exists()
    assert not (tmp_path / ".agents/skills/implement/SKILL.md").exists()
    playwright_skill = (tmp_path / ".agents/skills/playwright-testing/SKILL.md").read_text(encoding="utf-8")
    assert "npx playwright-cli" in playwright_skill
    assert "Navegar não é obrigatório" in playwright_skill
    assert "estrutura acessível" in playwright_skill
    assert "Sistema com persistência" in playwright_skill
    assert "persistence_not_executed" in playwright_skill
    assert "banco de teste isolado" in playwright_skill
    assert "nunca use “último registro”" in playwright_skill
    for source in agent_templates():
        installed = tmp_path / ".agents" / "skills" / source.parent.name / "SKILL.md"
        assert installed.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
        metadata = source.parent / "agents" / "openai.yaml"
        assert metadata.exists()
        installed_metadata = tmp_path / ".agents" / "skills" / source.parent.name / "agents" / "openai.yaml"
        assert installed_metadata.read_text(encoding="utf-8") == metadata.read_text(encoding="utf-8")
    assert not (tmp_path / "PLAYWRIGHT_GUIDE.md").exists()


def test_init_migrates_legacy_looper_state_and_text_references(tmp_path: Path):
    """Converte um projeto inicializado pelo STDD sem apagar seu estado.
    Move `.stdd` para `.looper` e atualiza referências textuais em arquivos do projeto.
    """
    legacy = tmp_path / ".stdd"
    (legacy / "draws").mkdir(parents=True)
    (legacy / "config.json").write_text('{"legacy": true}\n', encoding="utf-8")
    (legacy / "draws" / "journey.json").write_text(
        '{"draw_file": ".stdd/draws/journey.json", "tool": "STDD"}\n',
        encoding="utf-8",
    )
    (tmp_path / "AGENTS.md").write_text("Use stdd test e leia .stdd/config.json.\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("# STDD managed rules\n", encoding="utf-8")

    result = runner.invoke(app, ["init", str(tmp_path), "--integration", "codex"])
    assert result.exit_code == 0, result.output

    assert not legacy.exists()
    migrated_config = json.loads((tmp_path / ".looper/config.json").read_text(encoding="utf-8"))
    assert migrated_config["legacy"] is True
    migrated_draw = (tmp_path / ".looper/draws/journey.json").read_text(encoding="utf-8")
    assert "looper" in migrated_draw.lower()
    assert "stdd" not in migrated_draw.lower()
    assert "looper test" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "LOOPER managed rules" in (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert "STDD managed rules" not in (tmp_path / ".gitignore").read_text(encoding="utf-8")


def test_init_always_synchronizes_existing_agent_skills(tmp_path: Path):
    """Atualiza skills já instaladas sempre que o init é executado.
    Confirma que uma versão antiga recebe o template atual sem opção adicional.
    """
    init_project(tmp_path)
    skill = tmp_path / ".agents/skills/draw-system-level-3/SKILL.md"
    skill.write_text("versao antiga", encoding="utf-8")

    init_project(tmp_path)

    assert skill.read_text(encoding="utf-8") == Path("src/looper/templates/agents/draw-system-level-3/SKILL.md").read_text(encoding="utf-8")


def test_init_defers_language_specific_test_runner_to_setup(tmp_path: Path):
    """Mantém o init agnóstico e não escolhe um runner de linguagem antecipadamente.
    Chama init_project e verifica que a configuração inicial aguarda o setup da stack.
    """
    init_project(tmp_path)
    config = json.loads((tmp_path / ".looper/config.json").read_text())
    assert config["test_commands"] == []
    assert config["testing"]["profile"] == "mvp"
    assert config["backlog"]["bootstrap_task"] is True
    assert config["backlog"]["task_delivery_scope"] == "task"
    assert config["backlog"]["level_2_meaning"] == "Tela"
    assert config["backlog"]["level_3_meaning"] == "Regra de negócio e detalhes da tela"


def test_init_injects_agent_instruction_for_effective_development_mode(tmp_path: Path):
    """Renderiza no AGENTS.md a estratégia correspondente ao modo do init.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    init_project(tmp_path, development_mode="separated")
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "O modo é separado" in agents
    assert "todos os nós L2 como frontend/view" in agents
    assert "o loop de testes não cria testes para L2" in agents
    assert "O modo é conjunto" not in agents

    init_project(tmp_path, development_mode="sequential")
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "O modo é conjunto" in agents
    assert "O modo é separado" not in agents


def test_init_cli_persists_mode_before_installing_agent_instructions(tmp_path: Path):
    """A flag do init atualiza config e AGENTS.md na mesma inicialização.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    result = runner.invoke(app, ["init", str(tmp_path), "--development-mode", "separated"])

    assert result.exit_code == 0, result.output
    config = json.loads((tmp_path / ".looper/config.json").read_text(encoding="utf-8"))
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert config["backlog"]["development_mode"] == "separated"
    assert "O modo é separado" in agents


def test_init_creates_static_analysis_without_frontend_policy(tmp_path: Path):
    """Inicializa análise geral sem criar um gate frontend.
    Confirma defaults de segurança e exceções sem política específica de interface.
    """
    init_project(tmp_path)

    config = json.loads((tmp_path / ".looper/config.json").read_text())
    assert "frontend" not in config["static_analysis"]
    assert config["static_analysis"]["exceptions"] == []


def test_init_creates_persistent_loop_instructions_without_overwriting_it(tmp_path: Path):
    """Cria a mensagem crítica vazia e preserva edição do projeto.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    init_project(tmp_path)
    instructions = tmp_path / ".looper/loop-instructions.md"
    assert instructions.exists()
    assert instructions.read_text(encoding="utf-8") == ""
    instructions.write_text("Regra durável.", encoding="utf-8")
    init_project(tmp_path)
    assert instructions.read_text(encoding="utf-8") == "Regra durável."


def test_init_accepts_project_directory_argument(tmp_path: Path, monkeypatch):
    """Inicializa um projeto novo no diretório informado pelo usuário.
    Executa init com caminho relativo a outro diretório e confirma os artefatos no alvo.
    """
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "my-project"])

    assert result.exit_code == 0
    assert (tmp_path / "my-project/.looper/config.json").exists()
    assert (tmp_path / "my-project/.agents/skills/test-application/SKILL.md").exists()
    assert not (tmp_path / ".looper").exists()


def test_init_rejects_file_as_project_directory(tmp_path: Path):
    """Rejeita um arquivo como destino de inicialização do projeto.
    Cria um arquivo e confirma que init falha sem escrever ao lado dele.
    """
    target = tmp_path / "not-a-directory"
    target.write_text("existing")

    result = runner.invoke(app, ["init", str(target)])

    assert result.exit_code == 1
    assert "diretório" in result.output.lower()


def test_init_keeps_framework_artifacts_in_looper_and_agent_skills_in_agents(tmp_path: Path):
    """Mantém artefatos do framework em .looper e skills de agentes em .agents/skills.
    Inicializa um projeto vazio e verifica que nenhum outro diretório ou arquivo é criado na raiz.
    """
    init_project(tmp_path)

    assert {path.name for path in tmp_path.iterdir()} == {".looper", ".agents", ".gitignore", "AGENTS.md"}
    assert (tmp_path / ".agents/skills/test-application/SKILL.md").exists()
    assert (tmp_path / ".agents/conventions/README.md").exists()
    assert (tmp_path / ".agents/skills/implement-frontend/SKILL.md").exists()
    assert (tmp_path / ".agents/skills/implement-backend/SKILL.md").exists()
    assert not (tmp_path / ".agents/skills/implement-backlog").exists()
    assert (tmp_path / ".agents/skills/setup/SKILL.md").exists()
    assert not (tmp_path / ".agents/config.json").exists()
    assert (tmp_path / ".looper/config.json").exists()
    assert not (tmp_path / ".looper/draw.html").exists()
    assert (tmp_path / ".looper/draws/index.json").exists()
    assert (tmp_path / ".looper/draws/demo-inicial.json").exists()
    assert (tmp_path / ".looper/runs.html").exists()
    assert (tmp_path / ".looper/runs/index.json").exists()
    gitignore = (tmp_path / ".gitignore").read_text()
    assert ".env" in gitignore
    assert "*.pyc" in gitignore
    assert "__pycache__/" in gitignore
    assert ".cache/" in gitignore
    assert "*.cache" in gitignore
    assert ".coverage" in gitignore


def test_init_creates_conventions_index_without_overwriting_project_conventions(tmp_path: Path):
    """Cria o índice inicial e preserva convenções evoluídas pelo projeto.
    Executa init novamente depois de editar uma convenção local e confirma que o conteúdo permanece intacto.
    """
    init_project(tmp_path)
    assert sorted(path.name for path in (tmp_path / ".agents/conventions").glob("*.md")) == ["README.md"]
    convention = tmp_path / ".agents/conventions/backend.md"
    convention.write_text("# Backend\n\nDecisão confirmada do projeto.\n", encoding="utf-8")

    init_project(tmp_path)

    assert convention.read_text(encoding="utf-8") == "# Backend\n\nDecisão confirmada do projeto.\n"
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "## Convenções técnicas disponíveis" in agents
    assert "[Backend](.agents/conventions/backend.md)" in agents
    assert "Decisão confirmada do projeto." in agents


def test_init_update_does_not_inject_framework_conventions(tmp_path: Path):
    """Mantém a inicialização sem convenções padrão em novas sincronizações.
    Confirma que init repetido cria apenas o índice e preserva uma convenção do projeto.
    """
    init_project(tmp_path)
    project_convention = tmp_path / ".agents/conventions/project-rule.md"
    project_convention.write_text("---\nname: regra do projeto\ndescription: Decisão local.\n---\n", encoding="utf-8")

    init_project(tmp_path)

    assert project_convention.exists()
    assert not (tmp_path / ".agents/conventions/draw-specification-before-implementation.md").exists()
    assert not (tmp_path / ".agents/conventions/dynamic-screen-data.md").exists()
    assert sorted(path.name for path in (tmp_path / ".agents/conventions").glob("*.md")) == ["README.md", "project-rule.md"]


def test_init_injects_idempotent_instructions_for_all_agents(tmp_path: Path):
    """Atualiza os três arquivos locais de instruções sem duplicar o contrato Looper.
    Inicializa todas as integrações duas vezes e preserva o conteúdo previamente escrito pelo projeto.
    """
    (tmp_path / "AGENTS.md").write_text("# Regras do projeto\n\nNão remova este texto.\n", encoding="utf-8")

    init_project(tmp_path, integrations=("codex", "claude", "gemini"))
    first = {
        name: (tmp_path / name).read_text(encoding="utf-8")
        for name in ("AGENTS.md", "CLAUDE.md", "GEMINI.md")
    }
    init_project(tmp_path, integrations=("codex", "claude", "gemini"))

    for name, content in first.items():
        assert (tmp_path / name).read_text(encoding="utf-8") == content
        assert content.count("Looper:BEGIN AGENT INSTRUCTIONS") == 1
        assert "looper log" in content
        assert "commit" in content
        assert "push" in content
        assert "branch `main`" in content
        assert "uv tool install --force --editable ." not in content
        assert ".looper/design.html" in content
        assert "fonte obrigatória de decisões visuais" in content
        assert "Draws são a documentação oficial" in content
        assert "respeitando a hierarquia L2/L3" in content
    assert "Não remova este texto." in first["AGENTS.md"]


def test_init_uses_existing_claude_project_memory_file(tmp_path: Path):
    """Prefere a memória de projeto do Claude já existente quando ela está em .claude.
    Evita criar um segundo CLAUDE.md na raiz e preserva o conteúdo encontrado.
    """
    project_memory = tmp_path / ".claude/CLAUDE.md"
    project_memory.parent.mkdir()
    project_memory.write_text("# Claude do projeto\n", encoding="utf-8")

    init_project(tmp_path, integrations=("claude",))

    assert "Looper:BEGIN AGENT INSTRUCTIONS" in project_memory.read_text(encoding="utf-8")
    assert not (tmp_path / "CLAUDE.md").exists()


def test_init_preserves_existing_gitignore_and_does_not_duplicate_rules(tmp_path: Path):
    """Completa o gitignore existente sem apagar regras ou duplicar padrões Looper.
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
    Chama agent_templates e valida a presença dos títulos dos agentes create-tests, implement e setup.
    """
    templates = {template.parent.name: template for template in agent_templates()}
    assert set(templates) == {
        "backend-developer",
        "test-application",
        "draw-interaction",
        "draw-feature",
        "draw-improve",
        "draw-system-level-1",
        "draw-system-level-2",
        "draw-system-level-3",
        "draw-system-level-4",
        "implement-backend",
        "implement-frontend",
        "implement-change",
        "resolve-bug",
        "modern-web-guidance",
        "playwright-testing",
        "mock-server",
        "system-design",
        "setup",
        "static-analysis",
    }
    assert "# Test Application" in templates["test-application"].read_text()
    assert "# Backend Developer" in templates["backend-developer"].read_text()
    assert "# Implement Frontend Agent" in templates["implement-frontend"].read_text()
    assert "# Implement Backend Agent" in templates["implement-backend"].read_text()
    assert "servidores locais" in templates["mock-server"].read_text()
    backend_skill = templates["backend-developer"].read_text().lower()
    assert "exatamente quatro níveis" in backend_skill
    assert "`warn`" in backend_skill and "`info`" in backend_skill
    assert "credenciais deliberadamente inválidas" in backend_skill
    assert "console" in backend_skill and "banco de dados" in backend_skill
    assert "# Implement Change Agent" in templates["implement-change"].read_text()
    assert "looper backlog change" in templates["implement-change"].read_text().lower()
    assert "looper backlog complete <task-id>" in templates["implement-change"].read_text()
    assert "backlog-change-empty" in templates["implement-change"].read_text()
    assert "# Setup Agent" in templates["setup"].read_text()
    assert "# Modern Web Guidance" in templates["modern-web-guidance"].read_text()
    assert "# Playwright Testing" in templates["playwright-testing"].read_text()
    assert "complexidade ciclomática" in templates["static-analysis"].read_text()
    assert "long_function" in templates["static-analysis"].read_text()
    assert "acima de 150" in templates["static-analysis"].read_text()
    assert "Classe Deus" in templates["static-analysis"].read_text()
    assert "Etapa 1" in templates["static-analysis"].read_text()
    assert "hardcoded_secret" in templates["static-analysis"].read_text()
    assert "[REDACTED]" in templates["static-analysis"].read_text()
    assert "looper:allow-credential" in templates["static-analysis"].read_text()
    assert "allow_marked_test_credentials" in templates["static-analysis"].read_text()
    assert ".env" in templates["static-analysis"].read_text()
    assert "*.pyc" in templates["static-analysis"].read_text()
    assert "looper draw create" in templates["draw-feature"].read_text()
    assert "looper log" in templates["draw-feature"].read_text()
    for level in range(1, 5):
        assert "looper log" in templates[f"draw-system-level-{level}"].read_text()

    level_one = templates["draw-system-level-1"].read_text().lower()
    for required in ("nível 1", "parent_draw_ref", "parent_node_id", "root_draw_ref", "jornadas do usuário", "sem fluxos órfãos", "code_refs"):
        assert required in level_one
    level_two = templates["draw-system-level-2"].read_text().lower()
    for required in ("nível 2", "jornadas", "administrador", "permissões", "frontend/interface", "não implementado", "draw_ref", "draw.level2_missing_code_ref", "não deve bloquear"):
        assert required in level_two
    level_three = templates["draw-system-level-3"].read_text().lower()
    for required in ("nível 3", "dois lotes", "mais lotes", "ponta a ponta", "tudo o que é possível fazer", "chat", "marketplace", "code_refs", "source_dependencies", "no mínimo quatro nós", "no mínimo 80 caracteres", "warning", "draw.level3_min_nodes", "draw.level3_short_description", "description", "label", "edge.description", "obrigatoriedade de leitura do símbolo", "leitura prévia", "pode ser criado antes da implementação", "modo de especificação", "símbolo placeholder"):
        assert required in level_three
    level_four = templates["draw-system-level-4"].read_text().lower()
    for required in ("nível 4", "sob demanda", "qualified_name", "rpc", "procedure", "sql", "arquivo", "model"):
        assert required in level_four

    for required in ("supabase", "rpc", "back-end", "external_logic", "technologies", "sql_procedure", "sql_function", "localização da regra", "todos os níveis", "frontend/interface", "static_analysis.exceptions", "looper:ignore", "draw.level2_missing_code_ref", "draw.level3_min_nodes", "draw.level3_short_description", "menos de quatro nós", "menos de 80 caracteres", "somente `looper test` aplica o bloqueio"):
        assert required in templates["static-analysis"].read_text().lower()

    setup_content = templates["setup"].read_text()
    assert "núcleo do Looper permanece agnóstico" in setup_content
    assert "algoritmo deve ser próprio da stack detectada" in setup_content
    assert "Não começar pelo formato JSON" in setup_content
    assert "quality_findings" in setup_content
    assert "observed" in setup_content and "resolved" in setup_content and "unresolved" in setup_content
    assert "diretório do próprio projeto analisado" in setup_content
    assert "<project_root>/.looper/adapters/" in setup_content
    assert "não depender de serviço externo" in setup_content
    assert "personalizado para a linguagem e para a codebase" in setup_content
    assert "frontend-analysis" not in setup_content
    assert "static_analysis.exceptions" in setup_content

    backend_content = templates["implement-backend"].read_text()
    assert "Uso da análise estática para refatoração segura" in backend_content
    assert "101–150" in backend_content
    assert "valores antes/depois" in backend_content
    assert "300 linhas" in backend_content
    assert "não crie validação estática" in backend_content.lower()
    backend_developer_content = templates["backend-developer"].read_text().lower()
    assert "300 linhas" in backend_developer_content
    assert "não" in backend_developer_content and "validação estática" in backend_developer_content


def test_resolve_bug_skill_requires_observability_before_fix():
    """Exige diagnóstico observável antes da correção delegada do bug.
    Confirma subagente em tmux, validação do plano, stack trace e níveis de log.
    """
    content = Path("src/looper/templates/agents/resolve-bug/SKILL.md").read_text(encoding="utf-8")
    for required in (
        "tmux",
        "stack trace",
        "instrumentação diagnóstica",
        "`error`, `warn`, `info` e",
        "não os altere apenas por formalidade",
        "--type bug",
    ):
        assert required in content


def test_test_and_implement_skills_require_symbols_and_static_analysis_gate():
    """Exige rastreabilidade de símbolos nas skills de teste e implementação.
    Confirma que ambas instruem o agente a executar `looper test` antes de concluir.
    """
    for name in ("implement-backend", "implement-frontend"):
        content = Path(f"src/looper/templates/agents/{name}/SKILL.md").read_text(encoding="utf-8").lower()
        assert "associar" in content and "símbolo" in content
        assert "code_refs" in content
        assert "looper test" in content
        assert "looper draw associate-reference" in content
        assert "draw.level2_missing_code_ref" in content
        assert "draw.empty_node_symbol" in content


def test_test_and_implement_skills_require_explicit_draw_association_each_loop():
    """Impede que as skills tratem arquivo/símbolo como associação automática.
    Exige o comando e a verificação em cada ciclo de entrega.
    """
    for name in ("implement-backend", "implement-frontend"):
        content = Path(f"src/looper/templates/agents/{name}/SKILL.md").read_text(encoding="utf-8").lower()
        assert "a associação não é automática" in content
        assert "em todo loop" in content or "neste loop" in content
        assert "cada nó entregue" in content
        assert "qualified_name" in content
        assert "looper draw symbols" in content
        assert "--draw-id <draw-id>" in content
        assert "--node-id <node-id>" in content
        assert "--qualified-name" in content
        assert "--source-dependency" in content
        assert "antes de `backlog complete`" in content
        assert "só pode ser o último comando do loop" in content

    test_content = Path("src/looper/templates/agents/test-application/SKILL.md").read_text(encoding="utf-8").lower()
    assert "a associação não é automática" in test_content
    assert "cada nó entregue" in test_content
    assert "qualified_name" in test_content
    assert "looper draw symbols" in test_content
    assert "--qualified-name" in test_content


def test_implement_skill_requires_real_post_implementation_audit():
    """Impede que a verificação intermediária aprove código apenas por status.
    Exige leitura dos arquivos, comparação com o Draw, testes e evidências reais.
    """
    content = Path("src/looper/templates/agents/implement-backend/SKILL.md").read_text(encoding="utf-8").lower()

    for required in (
        "verificação intermediária da implementação",
        "auditoria obrigatória",
        "verification_interval",
        "arquivos e símbolos reais",
        "carregue esses arquivos no contexto",
        "compare a implementação com a especificação",
        "funciona de fato",
        "não pode concluir",
        "implementado",
        "parcial",
        "ausente",
        "bloqueado",
    ):
        assert required in content


def test_test_application_is_for_common_interactions_and_implement_skills_remain_backlog_scoped():
    """A skill transversal de testes é acionável fora do backlog; implementação permanece delimitada.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    for name, trigger in (("implement-frontend", "looper backlog frontend"), ("implement-backend", "looper backlog backend")):
        content = Path(f"src/looper/templates/agents/{name}/SKILL.md").read_text(encoding="utf-8").lower()
        assert "exclusivamente" in content
        assert trigger in content
        assert "não leia esta skill para edições comuns" in content

    installed_instructions = Path("AGENTS.md").read_text(encoding="utf-8").lower()
    assert "$test-application" in installed_instructions
    assert "$implement-frontend" in installed_instructions
    assert "$implement-backend" in installed_instructions
    assert "testes transversal" in installed_instructions
    assert "looper backlog complete <task-id>" in installed_instructions
    assert "o cursor não avança" in installed_instructions
    assert "implemente e teste ambos" in installed_instructions
    assert "não limita a entrega ao frontend" in installed_instructions


def test_contextual_memory_routes_durable_rules_to_the_right_document():
    """Mantém a memória do projeto seletiva e separa operação de design.
    Confirma que as skills orientam o registro durável sem transformar logs em contexto.
    """
    agents = Path("AGENTS.md").read_text(encoding="utf-8").lower()
    design = Path(".looper/design.html").read_text(encoding="utf-8").lower()

    assert "memória contextual seletiva" in agents
    assert "contratos, arquitetura, operação" not in agents
    assert ".agents/conventions/" in agents
    assert "não registre hipóteses" in agents
    assert "tokens" in design
    assert "4.5:1" in design
    assert "prefers-reduced-motion" in design
    for name in ("test-application", "implement-backend", "implement-frontend"):
        skill = Path(f"src/looper/templates/agents/{name}/SKILL.md").read_text(encoding="utf-8").lower()
        assert "memória contextual seletiva" in skill
        assert ".looper/design.html" in skill
        assert "não registre" in skill


def test_skills_route_specific_technical_memory_to_conventions():
    """Impede que Skills voltem a despejar contratos e detalhes técnicos no AGENTS.md.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    skill_paths = sorted(Path("src/looper/templates/agents").glob("*/SKILL.md"))
    contents = "\n".join(path.read_text(encoding="utf-8") for path in skill_paths)

    forbidden = (
        "registre no\n`AGENTS.md` o endpoint/contrato",
        "Registre contratos, arquitetura, operação, limites e escopo no `AGENTS.md`",
        "registe contratos gerais no `AGENTS.md`",
        "APIs e apps externos devem ser registrados no `AGENTS.md`",
        "Registre APIs/apps externos no `AGENTS.md`",
        "documenting a policy in CLAUDE.md or AGENTS.md",
    )
    for phrase in forbidden:
        assert phrase not in contents

    for skill_name in (
        "backend-developer",
        "implement-backend",
        "implement-frontend",
        "test-application",
        "draw-interaction",
        "setup",
        "modern-web-guidance",
    ):
        content = Path(f"src/looper/templates/agents/{skill_name}/SKILL.md").read_text(encoding="utf-8")
        assert ".agents/conventions/" in content, skill_name


def test_subagents_skill_documents_cli_contracts_and_non_polling_barrier():
    """Publica os comandos reais e proíbe polling para aguardar subagentes.
    Confirma o contrato de primeira chamada, retomada e espera observável.
    """
    # O contrato cobre tanto a primeira chamada quanto a retomada.
    # A espera deve ser bloqueante e acompanhável no Terminal do usuário.
    content = Path("src/looper/templates/agents/subagents/SKILL.md").read_text(encoding="utf-8")
    for required in ("codex exec", "claude -p", "agy -p", "--model", "--effort", "--resume", "--conversation", "tmux wait-for", "sem polling", "session_id"):
        assert required in content
    assert "tmux has-session" in content


def test_subagents_helper_discovers_local_agents():
    """O helper lista capacidades observáveis do PATH e versões locais.
    Confirma a descoberta sem selecionar agente ou modelo automaticamente.
    """
    # A descoberta reflete o ambiente sem escolher um modelo automaticamente.
    # O teste usa a mesma entrada recomendada pela skill.
    helper = Path("src/looper/templates/agents/subagents/scripts/orchestrate_subagents.py")
    result = subprocess.run([sys.executable, str(helper), "discover"], capture_output=True, text=True, check=False)
    assert result.returncode == 0
    discovered = json.loads(result.stdout)
    names = {entry["name"] for entry in discovered}
    assert {"codex", "claude", "agy"}.issubset(names)


def test_subagents_helper_reuses_tmux_pane_for_continuation():
    """Mantém o pane aberto e envia a continuação ao mesmo processo de shell.
    Confirma layout proporcional e o comando de retomada sem criar outra sessão.
    """
    # O pane precisa sobreviver ao fim do primeiro comando.
    # A continuação deve usar send-keys no alvo persistido.
    helper = Path("src/looper/templates/agents/subagents/scripts/orchestrate_subagents.py").read_text(encoding="utf-8")
    assert "split-window" in helper
    assert "even-horizontal" in helper
    assert "exec bash" in helper
    assert "send-keys" in helper


def test_frontend_dynamic_data_contract_is_published_and_injected(tmp_path: Path, monkeypatch):
    """Publica o contrato de dados dinâmicos nas skills e no AGENTS gerado.
    Confirma JSON único, chave explícita e adaptador get_mock_fake nas fontes distribuídas.
    """
    from looper.core import ensure_agent_instructions

    repository_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)
    source_skill = (repository_root / "src/looper/templates/agents/implement-frontend/SKILL.md").read_text(encoding="utf-8")
    installed_skill = (repository_root / ".agents/skills/implement-frontend/SKILL.md").read_text(encoding="utf-8")
    for content in (source_skill, installed_skill):
        assert "get_mock_fake" in content
        assert "JSON" in content
        assert "chave" in content.lower()
    assert "não crie um json por tela" in " ".join(source_skill.lower().split())

    ensure_agent_instructions(tmp_path, ("codex",))
    agent_instructions = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "Contrato de telas dinâmicas" in agent_instructions
    assert "get_mock_fake" in agent_instructions
    assert "sem salvar o símbolo da função de mock" in agent_instructions
    assert ".agents/conventions/dynamic-screen-data.md" not in agent_instructions
    assert "Contrato de telas dinâmicas" in agent_instructions


def test_node_delivery_contract_covers_tests_and_full_implementation():
    """Mantém explícito que `node` entrega a tela e todos os comportamentos internos.
    Confirma a regra nas skills de testes e de implementação do backlog.
    """
    implement = Path("src/looper/templates/agents/implement-backend/SKILL.md").read_text(encoding="utf-8").lower()
    create_tests = Path("src/looper/templates/agents/test-application/SKILL.md").read_text(encoding="utf-8").lower()
    normalized_implement = " ".join(implement.split())
    normalized_create_tests = " ".join(create_tests.split())

    for content in (implement, create_tests):
        assert "todos os subfluxos internos" in " ".join(content.split())
        assert "tela" in content
        assert "endpoints/handlers" in content
        assert "persistência" in content
        assert "integrações" in content
    assert "não reduz a cobertura à interface" in normalized_create_tests


def test_loop_skills_honor_disabled_test_phase():
    """Orienta os agentes a pular create-tests quando o init desabilitar testes.
    Mantém o cursor direcionado ao loop de implementação.
    """
    implement = Path("src/looper/templates/agents/implement-backend/SKILL.md").read_text(encoding="utf-8").lower()
    create_tests = Path("src/looper/templates/agents/test-application/SKILL.md").read_text(encoding="utf-8").lower()
    for content in (implement, create_tests):
        assert "test_loop_enabled: false" in content
        assert "loop de implementação" in content or "loop somente de implementação" in content
    assert "$test-application" in implement


def test_draw_system_level_three_splits_complete_detailed_screen_flows_into_phases():
    """Mantém o nível 3 em lotes completos, detalhando a tela por inteiro.
    Lê a skill publicada e impede fluxo estático, fase única ou desenho padronizado.
    """
    content = Path("src/looper/templates/agents/draw-system-level-3/SKILL.md").read_text(encoding="utf-8").lower()

    for required in (
        "dois lotes",
        "mais lotes",
        "lotes completos",
        "ponta a ponta",
        "tudo o que é possível fazer",
        "chat",
        "marketplace",
        "tela dinâmica",
        "quantidade fixa de nós",
        "quatro nós por padrão",
        "no mínimo quatro nós",
        "80 caracteres",
        "warning",
        "nós-gatilho",
        "cada ação",
        "ação de usuário",
        "fluxo genérico",
        "podem convergir",
        "pare e solicite confirmação",
    ):
        assert required in content

    assert "não trate uma tela dinâmica como sequência estática" in content


def test_draw_system_levels_keep_then_compatible_with_one_branch_family():
    """Mantém então como consequência certa sem permitir misturar se e ou.
    Lê cada template publicado e exige a convenção em todos os quatro níveis.
    """
    for level in range(1, 5):
        content = Path(f"src/looper/templates/agents/draw-system-level-{level}/SKILL.md").read_text(encoding="utf-8").lower()
        for required in (
            "convenção lógica de conexões",
            "consequência certa",
            "pode coexistir",
            "nunca misture `se` com `ou`",
            "pelo menos outro `se` correspondente",
            "nunca misture `ou` com `se`",
            "continuação inevitável",
        ):
            assert required in content, f"nível {level} não define {required}"


def test_implement_skill_triages_draw_diffs_before_declaring_no_change():
    """Exige que implement considere diffs de desenhos como contrato.
    Também impede concluir implementação sem uma alteração coerente pendente.
    """
    content = Path("src/looper/templates/agents/implement-backend/SKILL.md").read_text(encoding="utf-8").lower()

    for required in (
        "git diff -- .looper/draws",
        "git diff --cached -- .looper/draws",
        "arquivos não rastreados",
        "ler o json atual completo",
        "o diff de desenho é entrada de implementação",
        "pedido explícito de implementar",
        "fazer uma mudança coerente",
    ):
        assert required in content


def test_draw_improve_skill_is_incremental_and_hands_off_through_feature():
    """Limita cada melhoria do desenho e impede salto direto para produção.
    Confirma revisão humana, término sem alteração e sequência feature antes de implement.
    """
    content = Path("src/looper/templates/agents/draw-improve/SKILL.md").read_text(encoding="utf-8").lower()

    for required in (
        ".looper/draws/<draw-id>.json",
        ".looper/improvements/",
        "exatamente dez perguntas",
        "looper draw improve --pending",
        "status `applied`",
        "no máximo 3 novos nós",
        "já está bom",
        "um ciclo",
        "revisão",
        "$test-application",
        "$implement-backend",
        "looper draw diff",
        "somente alterações em `.looper/draws/*.json`",
        "gate de lacunas abertas pelas respostas",
        "nova sessão de acompanhamento",
        "quantidade necessária",
        "não marcar a sessão atual como `applied`",
    ):
        assert required in content
    assert "não pular" in content
    assert "100" not in content


def test_draw_improve_skill_requires_global_consistency_groups_and_questions():
    """Exige revisão integral, agrupamento e perguntas arquiteturais.
    Impede que a skill apenas acrescente nós sem corrigir o desenho existente.
    """
    content = Path("src/looper/templates/agents/draw-improve/SKILL.md").read_text(encoding="utf-8").lower()

    for required in (
        "revisão global",
        "todos os nós, relações, grupos, fluxos",
        "corrigir descrições vagas",
        "organizar os nós em grupos",
        "groups",
        "exatamente dez perguntas",
        "opções neutras",
        "não alterar `.looper/draws/<draw-id>.json`",
    ):
        assert required in content


def test_draw_answer_owns_question_discovery_and_codebase_traceability():
    """Isola respostas endereçadas e exige evidência de símbolos reais.
    Confirma que a skill usa o localizador oficial e separa resposta de associação.
    """
    content = Path("src/looper/templates/agents/draw-interaction/SKILL.md").read_text(encoding="utf-8").lower()
    for required in (
        "looper draw questions",
        "somente sobre os itens json retornados",
        "draw_file",
        "question_id",
        "@looper",
        "codebase",
        "símbolos",
        "code_refs",
        "não deve continuar aberta",
        "mantém a pergunta aberta",
        "qualified_name",
    ):
        assert required in content
    improve = Path("src/looper/templates/agents/draw-improve/SKILL.md").read_text(encoding="utf-8").lower()
    assert "draw-interaction" in improve
    assert "não responde" in improve


def test_draw_feature_matches_always_interactive_viewer():
    """Mantém a skill base alinhada ao Draw sem modo separado de edição.
    Rejeita instruções antigas sobre ativar edição ou usar inspetor.
    """
    content = Path("src/looper/templates/agents/draw-feature/SKILL.md").read_text(encoding="utf-8").lower()

    assert "ative `editar desenho`" not in content
    assert "inspetor" not in content
    assert "salvar alterações" in content


def test_draw_skills_document_questions_and_answer_history():
    """Documenta os tipos de pergunta e a persistência das respostas.
    Garante que as skills compartilhadas exponham o contrato da interação.
    """
    for name in ("draw-feature", "draw-improve", "draw-interaction"):
        content = Path(f"src/looper/templates/agents/{name}/SKILL.md").read_text(encoding="utf-8").lower()
        required_items = ("questions", "choice", "boolean", "open", "answer", "histórico")
        if name == "draw-improve":
            required_items += ("sem resposta", ".looper/improvements/")
        if name == "draw-interaction":
            required_items += ("@looper", "`false` e `0`")
        for required in required_items:
            assert required in content, f"{name} não define {required}"


def test_draw_skills_preserve_system_hierarchy_and_terminal_unimplemented_paths():
    """Alinha os agentes de desenho à árvore de arquitetura, jornada e implementação.
    Confirma que pai, filho e folhas ainda não implementadas são tratados sem órfãos.
    """
    for name in ("draw-feature", "draw-improve", "draw-system-level-1", "draw-system-level-2", "draw-system-level-3", "draw-system-level-4"):
        content = Path(f"src/looper/templates/agents/{name}/SKILL.md").read_text(encoding="utf-8").lower()
        for required in ("parent_draw_ref", "draw_ref", "órfãos"):
            assert required in content, f"{name} não define {required}"


def test_feature_and_implement_skills_honor_draw_system_boundaries():
    """Impede que testes ou produção ignorem a árvore de desenhos do sistema.
    Confirma leitura de pais, filhos, referências e folhas não implementadas.
    """
    for name in ("test-application", "implement-backend", "implement-frontend", "setup", "static-analysis"):
        content = Path(f"src/looper/templates/agents/{name}/SKILL.md").read_text(encoding="utf-8").lower()
        for required in ("draw-system", "parent_draw_ref", "parent_node_id", "root_draw_ref", "fluxo órfão"):
            assert required in content, f"{name} não define {required}"


def test_traceability_skills_cover_rpc_and_sql_implementations():
    """Cobre implementações RPC e SQL na checagem de símbolos.
    Mantém modelos como dependências opcionais, nunca como implementação principal.
    """
    for name in ("draw-system-level-4", "setup", "static-analysis"):
        content = Path(f"src/looper/templates/agents/{name}/SKILL.md").read_text(encoding="utf-8").lower()
        for required in ("rpc", "procedure", "sql", "arquivo", "model"):
            assert required in content, f"{name} não define {required}"


def test_setup_reports_missing_system_draw_without_creating_it():
    """Mantém setup separado da documentação arquitetural.
    Confirma que a verificação procura uma raiz, recomenda Draw System e não cria/edita o desenho.
    """
    content = Path("src/looper/templates/agents/setup/SKILL.md").read_text(encoding="utf-8").lower()
    for required in (".looper/draws/", "kind: \"system\"", "hierarchy.level: 1", "$draw-system-level-1", "não houver uma raiz de sistema", "não cria", "não deve editar o draw"):
        assert required in content


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
    """Exige que setup, create-tests e implement cubram testes funcionais e não funcionais.
    Valida contratos para IA real, banco, desempenho, segurança, isolamento e pentest.
    """
    templates = {template.parent.name: template.read_text(encoding="utf-8").lower() for template in agent_templates()}

    for name in ("setup", "test-application", "implement-backend"):
        content = templates[name]
        for required in ("teste live", "pgtap", "performance", "segurança", "isolamento", "pentest", "not_executed"):
            assert required in content, f"{name} não define {required}"
        for required in ("frontend", "markdown", "proporcional"):
            assert required in content, f"{name} não define a política proporcional para {required}"


def test_readme_documents_remote_install_and_interactive_integrations():
    """Mantém a documentação de instalação alinhada com a CLI pública.
    Verifica o comando remoto, a seleção múltipla e os três diretórios de integração.
    """
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "uv tool install --force --refresh looper --from git+https://github.com/MasterA10/looper.git@main" in readme
    assert "--all-integrations" in readme
    assert ".agents/skills/" in readme
    assert ".claude/skills/" in readme
    assert ".gemini/skills/" in readme
    assert "AGENTS.md" in readme
    assert "CLAUDE.md" in readme
    assert "GEMINI.md" in readme


def test_readme_documents_codex_skill_invocation():
    """Documenta como chamar as skills instaladas diretamente no terminal do Codex.
    Confirma que o README relaciona cada comando de skill ao objetivo do fluxo do Looper.
    """
    readme = Path("README.md").read_text(encoding="utf-8")

    for command in ("$setup", "$test-application", "$draw-feature", "$draw-improve", "$draw-interaction", "$draw-system-level-1", "$draw-system-level-2", "$draw-system-level-3", "$draw-system-level-4", "$static-analysis", "$implement-frontend", "$implement-backend"):
        assert command in readme
    assert ".agents/skills/<skill>/SKILL.md" in readme


def test_feature_skill_uses_tests_and_draw_json_without_markdown_copies():
    """Mantém testes e desenhos como fontes diretas da especificação da feature.
    Impede que a skill volte a criar request.md ou scenarios.md como cópias intermediárias.
    """
    content = (Path("src/looper/templates/agents/test-application/SKILL.md")).read_text(encoding="utf-8")

    assert ".looper/draws/<draw-id>.json" in content
    assert "request.md" not in content
    assert "scenarios.md" not in content


def test_setup_skill_defines_global_alias_and_database_lifecycle():
    """Exige um alias global que inclua runners com preparação e limpeza de banco.
    Valida que falhas não interrompem as suítes seguintes e aparecem no resultado consolidado.
    """
    content = Path("src/looper/templates/agents/setup/SKILL.md").read_text(encoding="utf-8").lower()

    for required in ("alias global", "todas as suítes", "migrations", "cleanup", "não interrompe"):
        assert required in content


def test_mock_server_skill_requires_strict_outbound_and_webhook_contracts():
    """Exige que a skill modele autenticação, ativação e recebimento em sequência.
    Lê o template e verifica os requisitos críticos do contrato.
    """
    content = Path("src/looper/templates/agents/mock-server/SKILL.md").read_text(encoding="utf-8").lower()

    for required in (
        "matriz do contrato",
        "credencial, formato e permissão",
        "ativação do recebimento",
        "transição explícita de estado",
        "bloqueado até a ativação",
        "assinatura",
        "não faça forwarding",
        "evento duplicado",
        "estado de ativação",
    ):
        assert required in content, f"mock-server não define {required}"


def test_init_injects_strict_mock_server_contract_instruction(tmp_path: Path):
    """Propaga a regra crítica para o construtor do AGENTS.md gerado pelo init.
    Inicializa um projeto temporário e verifica a instrução persistida.
    """
    init_project(tmp_path)
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8").lower()

    assert "$mock-server" in agents
    assert "recebimento por webhook" in agents
    assert "webhook ser ativado" in agents


def test_agent_skills_require_approval_for_expensive_or_mutating_setup():
    """Impede instalação, download e provisionamento sem autorização do usuário.
    Confirma que setup e implement preservam controle explícito em perfis flexíveis como MVP.
    """
    for name in ("setup", "implement-backend"):
        content = Path(f"src/looper/templates/agents/{name}/SKILL.md").read_text(encoding="utf-8").lower()
        for required in ("mvp", "aprovação explícita", "instalar", "baixar", "container", "criar banco"):
            assert required in content, f"{name} não define {required}"


def test_init_removes_retired_skills_automatically(tmp_path: Path):
    """Remove todas as skills legadas do histórico sem apagar skills atuais.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    legacy_names = {
        "create-tests",
        "create-tests-backlog",
        "draw-answer",
        "draw-system",
        "e2e-tester",
        "feature",
        "framework-check",
        "framework-fix",
        "framework-implement",
        "framework-init",
        "framework-security-scan",
        "framework-test-create",
        "framework-tradeoff",
        "implement",
        "implement-backlog",
        "missing",
        "open-design",
        "project-context",
        "quiz-generation",
        "speckit-analyze",
        "speckit-checklist",
        "speckit-clarify",
        "speckit-constitution",
        "speckit-git-commit",
        "speckit-git-feature",
        "speckit-git-initialize",
        "speckit-git-remote",
        "speckit-git-validate",
        "speckit-implement",
        "speckit-plan",
        "speckit-specify",
        "speckit-tasks",
        "speckit-taskstoissues",
    }
    for name in legacy_names:
        legacy_skill_dir = tmp_path / ".agents/skills" / name
        legacy_skill_dir.mkdir(parents=True)
        (legacy_skill_dir / "SKILL.md").write_text("conteudo obsoleto\n", encoding="utf-8")
    custom_skill = tmp_path / ".agents/skills/projeto-local/SKILL.md"
    custom_skill.parent.mkdir(parents=True)
    custom_skill.write_text("skill específica do projeto\n", encoding="utf-8")

    init_project(tmp_path)

    assert all(not (tmp_path / ".agents/skills" / name).exists() for name in legacy_names)
    assert custom_skill.read_text(encoding="utf-8") == "skill específica do projeto\n"
    assert (tmp_path / ".agents/skills/implement-frontend/SKILL.md").exists()
    assert (tmp_path / ".agents/skills/implement-backend/SKILL.md").exists()


def test_init_does_not_create_feature_or_implementation_commands():
    """Garante que a CLI pública do Looper expõe unicamente init e test.
    Invoca looper --help e assegura que create-tests e implement não constam na lista de comandos.
    """
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "init" in result.stdout
    assert "test" in result.stdout
    assert "create-tests" not in result.stdout
    assert "implement" not in result.stdout


def test_runs_viewer_is_read_only_and_uses_incremental_json_documents():
    """Mantém o viewer de runs restrito à leitura dos índices e relatórios JSON.
    Confirma que o template não contém comandos de gravação ou endpoints de alteração.
    """
    template = Path("src/looper/templates/runs/runs.html").read_text(encoding="utf-8")

    assert "fetch('runs/index.json')" in template
    assert "fetch(`runs/${day.summary}`)" in template
    assert "fetch(`runs/${day.snapshot}`)" in template
    assert "Somente leitura" in template
    assert "method: 'PUT'" not in template
    assert "method: 'POST'" not in template
    assert "method: 'DELETE'" not in template
    assert "writeText" not in template
