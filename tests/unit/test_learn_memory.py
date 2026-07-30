import json

from framework_cli.config.loader import save_config
from framework_cli.config.model import ProjectConfig
from framework_cli.learn.lifecycle import record, start
from framework_cli.learn.store import LearnStore


def enabled_config(tmp_path):
    config = ProjectConfig.default(tmp_path)
    config.learn["enabled"] = True
    save_config(tmp_path, config)


def test_learning_is_append_only_and_redacts_sensitive_values(tmp_path):
    enabled_config(tmp_path)
    assert start(tmp_path).status == "passed"
    result = record(tmp_path, "checkpoint", observations=["API_" + "KEY='hidden-" + "secret-value'"])
    assert result.status == "passed"
    events = (tmp_path / ".framework" / "learn" / "events" / "events.jsonl").read_text()
    assert "hidden-secret-value" not in events
    assert "redacted" in events
    assert len(LearnStore(tmp_path).events()) == 2


def test_disabled_learning_is_non_blocking(tmp_path):
    save_config(tmp_path, ProjectConfig.default(tmp_path))
    result = start(tmp_path)
    assert result.status == "disabled"
    assert result.exit_code == 0
