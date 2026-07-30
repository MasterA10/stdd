from framework_cli.commands.init import init_project


def test_init_with_integration_writes_only_framework_artifacts(tmp_path):
    (tmp_path / "app.py").write_text("x = 1")
    result = init_project(tmp_path, integration="claude")
    assert result.exit_code == 0
    assert (tmp_path / ".claude/commands/framework-check.md").exists()
    assert (tmp_path / "app.py").read_text() == "x = 1"
