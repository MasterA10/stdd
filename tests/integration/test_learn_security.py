from framework_cli.config.loader import save_config
from framework_cli.config.model import ProjectConfig
from framework_cli.learn.lifecycle import start
from framework_cli.learn.store import LearnStore
from framework_cli.security.scanner import SecurityScanner


def test_generated_memory_is_redacted_and_late_secret_is_blocked(tmp_path):
    config = ProjectConfig.default(tmp_path); config.learn["enabled"] = True; save_config(tmp_path, config)
    start(tmp_path)
    store = LearnStore(tmp_path)
    store.append_event({"event_id": "late", "session_id": "session", "type": "checkpoint",
                        "observations": ["TOKEN=" + "safe-redaction-value"]})
    events = (tmp_path / ".framework/learn/events/events.jsonl").read_text()
    assert "safe-redaction-value" not in events
    bad = tmp_path / ".framework/learn/quiz/late.json"
    bad.write_text("API_" + "KEY='" + "late-secret-value" + "'\n")
    assert SecurityScanner(tmp_path).scan(history=False).exit_code == 1
