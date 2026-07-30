from framework_cli.commands.init import init_project


def test_init_without_git_reports_degraded(tmp_path):
    result = init_project(tmp_path, integration="codex")
    assert result.status == "degraded"
    assert "history" in result.metadata["degraded"]
