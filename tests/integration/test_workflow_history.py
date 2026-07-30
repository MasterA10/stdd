import json

from framework_cli.commands.workflow import fix


def test_fix_creates_regression_and_complete_git_history_record(tmp_path):
    result = fix(tmp_path, "duplicate coupon application", agent_command="missing-agent")

    assert result.status == "prepared"
    regression = tmp_path / result.metadata["regression_test"]
    assert regression.exists()
    history = tmp_path / result.metadata["history_path"]
    record = json.loads(history.read_text())
    assert record["type"] == "bug"
    assert record["regression_test"] == result.metadata["regression_test"]
    assert "before" in record["git"] and "after" in record["git"]
    assert "related_files" in record["evidence"]
