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
    assert (tmp_path / ".agents/skills/create-tests/SKILL.md").exists()
    assert not (tmp_path / ".agents/skills/feature").exists()
    assert (tmp_path / ".agents/skills/implement/SKILL.md").exists()
    assert (tmp_path / ".agents/skills/setup/SKILL.md").exists()
    assert (tmp_path / ".agents/skills/static-analysis/SKILL.md").exists()
    assert (tmp_path / ".agents/skills/draw-feature/SKILL.md").exists()
    assert (tmp_path / ".agents/skills/draw-improve/SKILL.md").exists()
    assert (tmp_path / ".agents/skills/draw-answer/SKILL.md").exists()
    for level in range(1, 5):
        assert (tmp_path / ".agents/skills" / f"draw-system-level-{level}" / "SKILL.md").exists()
        assert (tmp_path / ".agents/skills" / f"draw-system-level-{level}" / "agents/openai.yaml").exists()
    assert (tmp_path / ".agents/skills/draw-improve/agents/openai.yaml").exists()
    assert (tmp_path / "AGENTS.md").exists()
    assert "stdd test" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "testes" in (tmp_path / ".agents/skills/create-tests/SKILL.md").read_text().lower()
    for source in agent_templates():
        installed = tmp_path / ".agents" / "skills" / source.parent.name / "SKILL.md"
        assert installed.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")


def test_init_always_synchronizes_existing_agent_skills(tmp_path: Path):
    """Atualiza skills já instaladas sempre que o init é executado.
    Confirma que uma versão antiga recebe o template atual sem opção adicional.
    """
    init_project(tmp_path)
    skill = tmp_path / ".agents/skills/draw-system-level-3/SKILL.md"
    skill.write_text("versao antiga", encoding="utf-8")

    init_project(tmp_path)

    assert skill.read_text(encoding="utf-8") == Path("src/stdd/templates/agents/draw-system-level-3/SKILL.md").read_text(encoding="utf-8")


def test_init_defers_language_specific_test_runner_to_setup(tmp_path: Path):
    """Mantém o init agnóstico e não escolhe um runner de linguagem antecipadamente.
    Chama init_project e verifica que a configuração inicial aguarda o setup da stack.
    """
    init_project(tmp_path)
    config = json.loads((tmp_path / ".stdd/config.json").read_text())
    assert config["test_commands"] == []
    assert config["testing"]["profile"] == "mvp"


def test_init_creates_static_analysis_without_frontend_policy(tmp_path: Path):
    """Inicializa análise geral sem criar um gate frontend.
    Confirma defaults de segurança e exceções sem política específica de interface.
    """
    init_project(tmp_path)

    config = json.loads((tmp_path / ".stdd/config.json").read_text())
    assert "frontend" not in config["static_analysis"]
    assert config["static_analysis"]["exceptions"] == []


def test_init_accepts_project_directory_argument(tmp_path: Path, monkeypatch):
    """Inicializa um projeto novo no diretório informado pelo usuário.
    Executa init com caminho relativo a outro diretório e confirma os artefatos no alvo.
    """
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "my-project"])

    assert result.exit_code == 0
    assert (tmp_path / "my-project/.stdd/config.json").exists()
    assert (tmp_path / "my-project/.agents/skills/create-tests/SKILL.md").exists()
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

    assert {path.name for path in tmp_path.iterdir()} == {".stdd", ".agents", ".gitignore", "AGENTS.md"}
    assert (tmp_path / ".agents/skills/create-tests/SKILL.md").exists()
    assert (tmp_path / ".agents/skills/implement/SKILL.md").exists()
    assert (tmp_path / ".agents/skills/setup/SKILL.md").exists()
    assert not (tmp_path / ".agents/config.json").exists()
    assert (tmp_path / ".stdd/config.json").exists()
    assert not (tmp_path / ".stdd/draw.html").exists()
    assert (tmp_path / ".stdd/draws/index.json").exists()
    assert (tmp_path / ".stdd/draws/demo-inicial.json").exists()
    assert (tmp_path / ".stdd/runs.html").exists()
    assert (tmp_path / ".stdd/runs/index.json").exists()
    gitignore = (tmp_path / ".gitignore").read_text()
    assert ".env" in gitignore
    assert "*.pyc" in gitignore
    assert "__pycache__/" in gitignore
    assert ".cache/" in gitignore
    assert "*.cache" in gitignore
    assert ".coverage" in gitignore


def test_init_injects_idempotent_instructions_for_all_agents(tmp_path: Path):
    """Atualiza os três arquivos locais de instruções sem duplicar o contrato STDD.
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
        assert content.count("STDD:BEGIN AGENT INSTRUCTIONS") == 1
        assert "stdd log" in content
        assert "commit" in content
        assert "push" in content
        assert "branch `main`" in content
        assert "uv tool install --force --editable ." in content
    assert "Não remova este texto." in first["AGENTS.md"]


def test_init_uses_existing_claude_project_memory_file(tmp_path: Path):
    """Prefere a memória de projeto do Claude já existente quando ela está em .claude.
    Evita criar um segundo CLAUDE.md na raiz e preserva o conteúdo encontrado.
    """
    project_memory = tmp_path / ".claude/CLAUDE.md"
    project_memory.parent.mkdir()
    project_memory.write_text("# Claude do projeto\n", encoding="utf-8")

    init_project(tmp_path, integrations=("claude",))

    assert "STDD:BEGIN AGENT INSTRUCTIONS" in project_memory.read_text(encoding="utf-8")
    assert not (tmp_path / "CLAUDE.md").exists()


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
    Chama agent_templates e valida a presença dos títulos dos agentes create-tests, implement e setup.
    """
    templates = {template.parent.name: template for template in agent_templates()}
    assert set(templates) == {"create-tests", "draw-answer", "draw-feature", "draw-improve", "draw-system-level-1", "draw-system-level-2", "draw-system-level-3", "draw-system-level-4", "implement", "setup", "static-analysis"}
    assert "# Create Tests Agent" in templates["create-tests"].read_text()
    assert "# Implement Agent" in templates["implement"].read_text()
    assert "# Setup Agent" in templates["setup"].read_text()
    assert "complexidade ciclomática" in templates["static-analysis"].read_text()
    assert "long_function" in templates["static-analysis"].read_text()
    assert "acima de 150" in templates["static-analysis"].read_text()
    assert "Classe Deus" in templates["static-analysis"].read_text()
    assert "Etapa 1" in templates["static-analysis"].read_text()
    assert "hardcoded_secret" in templates["static-analysis"].read_text()
    assert "[REDACTED]" in templates["static-analysis"].read_text()
    assert "stdd:allow-credential" in templates["static-analysis"].read_text()
    assert "allow_marked_test_credentials" in templates["static-analysis"].read_text()
    assert ".env" in templates["static-analysis"].read_text()
    assert "*.pyc" in templates["static-analysis"].read_text()
    assert "stdd draw create" in templates["draw-feature"].read_text()
    assert "stdd log" in templates["draw-feature"].read_text()
    for level in range(1, 5):
        assert "stdd log" in templates[f"draw-system-level-{level}"].read_text()

    level_one = templates["draw-system-level-1"].read_text().lower()
    for required in ("nível 1", "parent_draw_ref", "parent_node_id", "root_draw_ref", "jornadas do usuário", "sem fluxos órfãos", "code_refs"):
        assert required in level_one
    level_two = templates["draw-system-level-2"].read_text().lower()
    for required in ("nível 2", "jornadas", "administrador", "permissões", "frontend/interface", "não implementado", "draw_ref", "draw.level2_missing_code_ref", "nunca bloqueia"):
        assert required in level_two
    level_three = templates["draw-system-level-3"].read_text().lower()
    for required in ("nível 3", "dois lotes", "mais lotes", "ponta a ponta", "tudo o que é possível fazer", "chat", "marketplace", "code_refs", "source_dependencies", "no mínimo quatro nós", "no mínimo 80 caracteres", "warning", "draw.level3_min_nodes", "draw.level3_short_description", "description", "label", "edge.description"):
        assert required in level_three
    level_four = templates["draw-system-level-4"].read_text().lower()
    for required in ("nível 4", "sob demanda", "qualified_name", "rpc", "procedure", "sql", "arquivo", "model"):
        assert required in level_four

    for required in ("supabase", "rpc", "back-end", "external_logic", "technologies", "sql_procedure", "sql_function", "localização da regra", "todos os níveis", "frontend/interface", "static_analysis.exceptions", "stdd:ignore", "draw.level2_missing_code_ref", "draw.level3_min_nodes", "draw.level3_short_description", "menos de quatro nós", "menos de 80 caracteres", "nunca bloqueiam"):
        assert required in templates["static-analysis"].read_text().lower()

    setup_content = templates["setup"].read_text()
    assert "núcleo do STDD permanece agnóstico" in setup_content
    assert "algoritmo deve ser próprio da stack detectada" in setup_content
    assert "Não começar pelo formato JSON" in setup_content
    assert "quality_findings" in setup_content
    assert "observed" in setup_content and "resolved" in setup_content and "unresolved" in setup_content
    assert "diretório do próprio projeto analisado" in setup_content
    assert "<project_root>/.stdd/adapters/" in setup_content
    assert "não depender de serviço externo" in setup_content
    assert "personalizado para a linguagem e para a codebase" in setup_content
    assert "frontend-analysis" not in setup_content
    assert "static_analysis.exceptions" in setup_content

    implement_content = templates["implement"].read_text()
    assert "Uso da análise estática para refatoração segura" in implement_content
    assert "101–150" in implement_content
    assert "valores antes/depois" in implement_content


def test_draw_system_level_three_splits_complete_detailed_screen_flows_into_phases():
    """Mantém o nível 3 em lotes completos, detalhando a tela por inteiro.
    Lê a skill publicada e impede fluxo estático, fase única ou desenho padronizado.
    """
    content = Path("src/stdd/templates/agents/draw-system-level-3/SKILL.md").read_text(encoding="utf-8").lower()

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
        content = Path(f"src/stdd/templates/agents/draw-system-level-{level}/SKILL.md").read_text(encoding="utf-8").lower()
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
    content = Path("src/stdd/templates/agents/implement/SKILL.md").read_text(encoding="utf-8").lower()

    for required in (
        "git diff -- .stdd/draws",
        "git diff --cached -- .stdd/draws",
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
    content = Path("src/stdd/templates/agents/draw-improve/SKILL.md").read_text(encoding="utf-8").lower()

    for required in (
        ".stdd/draws/<draw-id>.json",
        "no máximo 3 novos nós",
        "já está bom",
        "um ciclo",
        "revisão",
        "$create-tests",
        "$implement",
        "estado vermelho",
        "stdd draw diff",
        "somente alterações em `.stdd/draws/*.json`",
    ):
        assert required in content
    assert "não pular" in content
    assert "100" not in content


def test_draw_improve_skill_requires_global_consistency_groups_and_questions():
    """Exige revisão integral, agrupamento e perguntas arquiteturais.
    Impede que a skill apenas acrescente nós sem corrigir o desenho existente.
    """
    content = Path("src/stdd/templates/agents/draw-improve/SKILL.md").read_text(encoding="utf-8").lower()

    for required in (
        "revisão global obrigatória",
        "todos os nós, relações, grupos, fluxos",
        "corrigir descrições vagas",
        "organizar os nós em grupos",
        "groups",
        "pelo menos 5 perguntas arquiteturais",
        "opções neutros",
        "sugestão arquitetural separadamente na resposta",
    ):
        assert required in content


def test_draw_answer_owns_question_discovery_and_codebase_traceability():
    """Isola respostas endereçadas e exige evidência de símbolos reais.
    Confirma que a skill usa o localizador oficial e separa resposta de associação.
    """
    content = Path("src/stdd/templates/agents/draw-answer/SKILL.md").read_text(encoding="utf-8").lower()
    for required in (
        "stdd draw questions",
        "somente sobre os itens json retornados",
        "draw_file",
        "question_id",
        "@stdd",
        "codebase",
        "símbolos",
        "code_refs",
        "não deve continuar aberta",
        "mantém a pergunta aberta",
        "qualified_name",
    ):
        assert required in content
    improve = Path("src/stdd/templates/agents/draw-improve/SKILL.md").read_text(encoding="utf-8").lower()
    assert "draw-answer" in improve
    assert "não responde" in improve


def test_draw_feature_matches_always_interactive_viewer():
    """Mantém a skill base alinhada ao Draw sem modo separado de edição.
    Rejeita instruções antigas sobre ativar edição ou usar inspetor.
    """
    content = Path("src/stdd/templates/agents/draw-feature/SKILL.md").read_text(encoding="utf-8").lower()

    assert "ative `editar desenho`" not in content
    assert "inspetor" not in content
    assert "salvar alterações" in content


def test_draw_skills_document_optional_questions_and_answer_history():
    """Documenta perguntas opcionais como decisões persistentes do desenho.
    Confirma suporte a escolha, sim ou não, resposta aberta e histórico respondido.
    """
    for name in ("draw-feature", "draw-improve", "draw-answer"):
        content = Path(f"src/stdd/templates/agents/{name}/SKILL.md").read_text(encoding="utf-8").lower()
        required_items = ("questions", "choice", "boolean", "open", "answer", "histórico", "sem resposta")
        if name == "draw-answer":
            required_items += ("@stdd", "`false` e `0`")
        for required in required_items:
            assert required in content, f"{name} não define {required}"


def test_draw_skills_preserve_system_hierarchy_and_terminal_unimplemented_paths():
    """Alinha os agentes de desenho à árvore de arquitetura, jornada e implementação.
    Confirma que pai, filho e folhas ainda não implementadas são tratados sem órfãos.
    """
    for name in ("draw-feature", "draw-improve", "draw-system-level-1", "draw-system-level-2", "draw-system-level-3", "draw-system-level-4"):
        content = Path(f"src/stdd/templates/agents/{name}/SKILL.md").read_text(encoding="utf-8").lower()
        for required in ("parent_draw_ref", "draw_ref", "órfãos"):
            assert required in content, f"{name} não define {required}"


def test_feature_and_implement_skills_honor_draw_system_boundaries():
    """Impede que testes ou produção ignorem a árvore de desenhos do sistema.
    Confirma leitura de pais, filhos, referências e folhas não implementadas.
    """
    for name in ("create-tests", "implement", "setup", "static-analysis"):
        content = Path(f"src/stdd/templates/agents/{name}/SKILL.md").read_text(encoding="utf-8").lower()
        for required in ("draw-system", "parent_draw_ref", "parent_node_id", "root_draw_ref", "fluxo órfão"):
            assert required in content, f"{name} não define {required}"


def test_traceability_skills_cover_rpc_and_sql_implementations():
    """Cobre implementações RPC e SQL na checagem de símbolos.
    Mantém modelos como dependências opcionais, nunca como implementação principal.
    """
    for name in ("draw-system-level-4", "setup", "static-analysis"):
        content = Path(f"src/stdd/templates/agents/{name}/SKILL.md").read_text(encoding="utf-8").lower()
        for required in ("rpc", "procedure", "sql", "arquivo", "model"):
            assert required in content, f"{name} não define {required}"


def test_setup_reports_missing_system_draw_without_creating_it():
    """Mantém setup separado da documentação arquitetural.
    Confirma que a verificação procura uma raiz, recomenda Draw System e não cria/edita o desenho.
    """
    content = Path("src/stdd/templates/agents/setup/SKILL.md").read_text(encoding="utf-8").lower()
    for required in (".stdd/draws/", "kind: \"system\"", "hierarchy.level: 1", "$draw-system-level-1", "não houver uma raiz de sistema", "não cria", "não deve editar o draw"):
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

    for name in ("setup", "create-tests", "implement"):
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

    assert "uv tool install --force --refresh stdd --from git+https://github.com/MasterA10/stdd.git@main" in readme
    assert "--all-integrations" in readme
    assert ".agents/skills/" in readme
    assert ".claude/skills/" in readme
    assert ".gemini/skills/" in readme
    assert "AGENTS.md" in readme
    assert "CLAUDE.md" in readme
    assert "GEMINI.md" in readme


def test_readme_documents_codex_skill_invocation():
    """Documenta como chamar as skills instaladas diretamente no terminal do Codex.
    Confirma que o README relaciona cada comando de skill ao objetivo do fluxo do STDD.
    """
    readme = Path("README.md").read_text(encoding="utf-8")

    for command in ("$setup", "$create-tests", "$draw-feature", "$draw-improve", "$draw-answer", "$draw-system-level-1", "$draw-system-level-2", "$draw-system-level-3", "$draw-system-level-4", "$static-analysis", "$implement"):
        assert command in readme
    assert ".agents/skills/<skill>/SKILL.md" in readme


def test_feature_skill_uses_tests_and_draw_json_without_markdown_copies():
    """Mantém testes e desenhos como fontes diretas da especificação da feature.
    Impede que a skill volte a criar request.md ou scenarios.md como cópias intermediárias.
    """
    content = (Path("src/stdd/templates/agents/create-tests/SKILL.md")).read_text(encoding="utf-8")

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
    Invoca stdd --help e assegura que create-tests e implement não constam na lista de comandos.
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
    template = Path("src/stdd/templates/runs/runs.html").read_text(encoding="utf-8")

    assert "fetch('runs/index.json')" in template
    assert "fetch(`runs/${day.summary}`)" in template
    assert "fetch(`runs/${day.snapshot}`)" in template
    assert "Somente leitura" in template
    assert "method: 'PUT'" not in template
    assert "method: 'POST'" not in template
    assert "method: 'DELETE'" not in template
    assert "writeText" not in template
