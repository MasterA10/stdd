from typer.testing import CliRunner

from looper.cli import app
from looper.tui import KeyboardTUI, apply_backlog_form, load_documents, save_documents, validate_documents


def test_tui_documents_cover_all_persistent_configuration_files(tmp_path):
    """Carrega todas as superfícies de configuração editáveis pela TUI.
    Inicializa um projeto temporário e confirma config, revisão e instruções críticas.
    """
    documents = load_documents(tmp_path)
    assert set(documents) == {"config", "review", "instructions"}
    assert (tmp_path / ".looper/config.json").exists()
    assert (tmp_path / ".looper/review-agents.json").exists()


def test_tui_save_preserves_unknown_keys_and_instructions(tmp_path):
    """Persiste alterações sem perder chaves de versões futuras.
    Adiciona uma chave desconhecida, salva os documentos e relê o conteúdo completo.
    """
    documents = load_documents(tmp_path)
    documents["config"]["future_option"] = {"enabled": True}
    documents["review"]["future_agent_option"] = "preserve"
    documents["instructions"] = "Sempre validar o contexto."
    save_documents(tmp_path, documents)
    loaded = load_documents(tmp_path)
    assert loaded["config"]["future_option"]["enabled"] is True
    assert loaded["review"]["future_agent_option"] == "preserve"
    assert loaded["instructions"] == "Sempre validar o contexto."


def test_tui_backlog_form_updates_guided_values_without_erasing_advanced_config():
    """Aplica campos guiados mantendo opções avançadas do backlog.
    Atualiza loops, lote e modo e confirma que uma chave customizada continua presente.
    """
    config = {"backlog": {"custom_option": "keep", "test_loop": {}, "implementation_loop": {}}}
    updated = apply_backlog_form(config, {"development_mode": "separated", "task_delivery_scope": "node", "task_batch_size": "2", "task_batch_scope": "node", "test_mode": "all_level2_then_level3", "test_l2_children_mode": "context", "implementation_mode": "node_then_children", "implementation_l2_children_mode": "owned", "test_loop_enabled": False, "test_l3_loop_enabled": False, "implementation_l3_loop_enabled": True, "test_l3_include_parent": True})
    assert updated["backlog"]["development_mode"] == "separated"
    assert updated["backlog"]["custom_option"] == "keep"
    assert updated["backlog"]["test_loop"]["l2_children_mode"] == "context"
    assert updated["backlog"]["implementation_loop"]["l2_children_mode"] == "owned"


def test_tui_rejects_invalid_loop_configuration(tmp_path):
    """Impede salvar modos de loop desconhecidos.
    Carrega defaults, injeta um valor inválido e confirma a mensagem de validação.
    """
    documents = load_documents(tmp_path)
    documents["config"]["backlog"]["development_mode"] = "invalid"
    try:
        validate_documents(documents["config"], documents["review"], documents["instructions"])
    except ValueError as error:
        assert "development_mode" in str(error)
    else:
        raise AssertionError("configuração inválida foi aceita")


def test_keyboard_tui_has_keyboard_pages_and_actions(tmp_path):
    """Expõe páginas e ações sem exigir componentes de mouse.
    Usa um objeto mínimo de tela para confirmar o catálogo navegável da TUI.
    """
    class Screen:
        pass

    tui = KeyboardTUI(Screen(), tmp_path)
    assert [name for name, _ in tui.PAGES] == ["init", "backlog", "config", "review", "instructions"]
    assert tui.handle("2") is False
    assert tui.page == 1
    assert tui.handle( ord("5") ) is False
    assert tui.page == 4
    tui.field = 2
    assert tui.handle("\x1b") is False
    assert (tui.page, tui.field) == (0, 0)
    assert tui.handle(3) is True


def test_tui_contextual_help_explains_selected_option(tmp_path):
    """Explica o efeito e o caminho da opção sem abrir editor textual."""
    class Screen:
        pass

    tui = KeyboardTUI(Screen(), tmp_path)
    assert "loop" in tui.help_for("test_mode")
    assert tui.help_path("test_mode") == ".looper/config.json:backlog.test_loop"
    assert "revisão" in tui.help_for("review_enabled")


def test_tui_cli_aliases_are_available():
    """Expõe os dois comandos públicos da interface de configuração.
    Consulta a ajuda da CLI e confirma que tui e config tui são reconhecidos.
    """
    runner = CliRunner()
    assert runner.invoke(app, ["tui", "--help"]).exit_code == 0
    assert runner.invoke(app, ["config", "tui", "--help"]).exit_code == 0
