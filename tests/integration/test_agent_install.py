from framework_cli.commands.install import install


def test_install_supports_both_agents(tmp_path):
    result = install(tmp_path, "codex")
    assert result.exit_code == 0
    result = install(tmp_path, "claude")
    assert result.exit_code == 0
