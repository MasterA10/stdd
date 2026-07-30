import json
from datetime import date, timedelta

from framework_cli.config.loader import save_config
from framework_cli.config.model import ProjectConfig
from framework_cli.learn.store import LearnStore


def test_learn_store_enforces_configured_retention(tmp_path):
    config = ProjectConfig.default(tmp_path)
    config.learn.update({"enabled": True, "retention_days": 1})
    save_config(tmp_path, config)
    events = tmp_path / ".framework" / "learn" / "events" / "events.jsonl"
    events.parent.mkdir(parents=True, exist_ok=True)
    old = {"event_id": "old", "session_id": "session", "type": "checkpoint",
           "local_date": (date.today() - timedelta(days=3)).isoformat()}
    events.write_text(json.dumps(old) + "\n")

    store = LearnStore(tmp_path)

    assert store.events() == []
    assert store.retention_report["removed"] == 1
    assert (tmp_path / ".framework" / "learn" / "retention.jsonl").exists()
