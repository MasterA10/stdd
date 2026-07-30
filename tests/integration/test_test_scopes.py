from framework_cli.cli import build_parser
from framework_cli.commands.test import run_tests
from framework_cli.commands.workflow import _configured_command, generate_scripts


def _tests(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='scope-fixture'\n")
    (tmp_path / "tests/unit").mkdir(parents=True)
    (tmp_path / "tests/integration").mkdir(parents=True)
    (tmp_path / "tests/unit/test_unit.py").write_text("def test_unit():\n    assert True\n")
    (tmp_path / "tests/integration/test_integration.py").write_text("def test_integration():\n    assert True\n")


def test_test_scope_runs_only_selected_directory(tmp_path):
    _tests(tmp_path)

    result = run_tests(tmp_path, scope="unit")

    assert result.exit_code == 0
    assert result.metadata["scope"] == "unit"
    assert result.children[0]["command"][-1] == "tests/unit"


def test_test_run_honors_an_explicit_test_path(tmp_path):
    _tests(tmp_path)

    result = run_tests(tmp_path, explicit_paths=["tests/integration/test_integration.py"])

    assert result.exit_code == 0
    assert result.metadata["paths"] == ["tests/integration/test_integration.py"]
    assert result.children[0]["command"][-1] == "tests/integration/test_integration.py"


def test_all_flag_is_available_and_includes_security_child():
    args = build_parser().parse_args(["test", "--all"])

    assert args.all is True
    assert args.test_command is None


def test_local_agent_is_selected_when_no_agent_argument_is_given(tmp_path, monkeypatch):
    monkeypatch.setattr("framework_cli.commands.workflow.shutil.which",
                        lambda name: "/usr/local/bin/codex" if name == "codex" else None)

    command = _configured_command(tmp_path, None)

    assert command == (["/usr/local/bin/codex", "exec", "-C", str(tmp_path.resolve()), "-"], True)


def test_script_generation_prepares_redacted_agent_request_without_agent(tmp_path, monkeypatch):
    monkeypatch.setattr("framework_cli.commands.workflow.shutil.which", lambda _name: None)

    result = generate_scripts(tmp_path)

    assert result.metadata["status"] == "prepared"
    assert (tmp_path / result.metadata["request_path"]).exists()
