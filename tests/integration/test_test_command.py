from framework_cli.commands.test import run_tests


def test_test_command_aggregates_runner_results(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    result = run_tests(tmp_path)
    assert result.children
    assert result.exit_code == 0 or result.status in {"degraded", "blocked"}
