from framework_cli.config.loader import save_config
from framework_cli.config.model import ProjectConfig
from framework_cli.cli import build_parser
from framework_cli.testing.approval import approval_findings, approve_all_tests, approve_test


def _project(tmp_path, profile="mvp"):
    config = ProjectConfig.default(tmp_path)
    config.profile = profile
    save_config(tmp_path, config)
    test = tmp_path / "tests" / "test_behavior.py"
    test.parent.mkdir(exist_ok=True)
    test.write_text("def test_behavior():\n    assert True\n")
    return test


def test_approval_hash_blocks_modified_test_in_mvp(tmp_path):
    test = _project(tmp_path)
    assert approve_test(tmp_path, "tests/test_behavior.py").exit_code == 0

    test.write_text("def test_behavior():\n    assert False\n")

    findings = approval_findings(tmp_path)
    assert len(findings) == 1
    assert findings[0].severity == "block"
    assert findings[0].rule == "approved-test-modified"


def test_experiment_profile_warns_instead_of_blocking(tmp_path):
    test = _project(tmp_path, profile="experiment")
    approve_test(tmp_path, "tests/test_behavior.py")
    test.write_text("def test_behavior():\n    assert False\n")

    assert approval_findings(tmp_path)[0].severity == "warning"


def test_approve_without_path_approves_all_discovered_tests(tmp_path):
    _project(tmp_path)
    second = tmp_path / "tests" / "test_other.py"
    second.write_text("def test_other():\n    assert True\n")

    result = approve_all_tests(tmp_path)

    assert result.metadata["count"] == 2
    assert set(result.metadata["approved"]) == {"tests/test_behavior.py", "tests/test_other.py"}


def test_explain_and_approve_paths_are_optional_in_cli():
    explain = build_parser().parse_args(["test", "explain"])
    approve = build_parser().parse_args(["test", "approve"])

    assert explain.test_path is None
    assert approve.test_path is None


def test_agentic_test_commands_accept_complete_descriptions():
    args = build_parser().parse_args([
        "test", "create", "A", "complete", "feature", "description",
        "--agent-command", "codex",
    ])
    assert args.description == ["A", "complete", "feature", "description"]
    assert args.agent_command == "codex"
