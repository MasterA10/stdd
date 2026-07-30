from framework_cli.commands.workflow import create_test, implement, tradeoff
from framework_cli.testing.explanations import explain_test


def test_create_and_agent_request_respect_instruction_chain(tmp_path):
    created = create_test(tmp_path, "total must not be negative", path="tests/test_total.py")
    assert created.exit_code == 0
    assert (tmp_path / "tests/test_total.py").exists()

    result = implement(tmp_path, "tests/test_total.py")

    assert result.exit_code == 0
    assert result.metadata["status"] == "prepared"
    requests = list((tmp_path / ".framework/agents/requests").glob("*.json"))
    assert len(requests) == 1
    assert "stdout" not in requests[0].read_text()


def test_agentic_command_is_blocked_by_instruction_conflict(tmp_path):
    (tmp_path / "AGENTS.md").write_text("CONFLICT: local instructions disagree\n")

    result = tradeoff(tmp_path, "sync or async processing")

    assert result.status == "blocked"
    assert result.exit_code == 1


def test_explain_all_only_updates_test_files(tmp_path):
    (tmp_path / "app.py").write_text("def value():\n    return 1\n")
    test = tmp_path / "tests/test_value.py"
    test.parent.mkdir()
    test.write_text("from app import value\n\ndef test_value():\n    assert value() == 1\n")

    result = explain_test(tmp_path, "tests/test_value.py", mode="first-use")

    assert result.metadata["symbols"][0]["name"] == "value"
    assert "@framework:explanations:start" in test.read_text()
