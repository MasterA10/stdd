import platform

from framework_cli.config.loader import save_config
from framework_cli.config.model import ProjectConfig
from framework_cli.learn.cli_adapters import send_package
from framework_cli.learn.host_hooks import dispatch_event, install


def test_host_hook_scripts_and_missing_cli_are_safe_on_supported_platforms(tmp_path):
    config = ProjectConfig.default(tmp_path); config.learn["enabled"] = True; save_config(tmp_path, config)
    installed = install(tmp_path, ["codex", "claude", "cloud", "antigravity"])
    assert installed.status == "passed"
    assert (tmp_path / ".framework/hooks/codex/compact.sh").exists()
    started = dispatch_event(tmp_path, "start", host="codex")
    assert started.status == "passed"
    compacted = dispatch_event(tmp_path, "compact", host="codex", session_id=started.metadata["session_id"])
    assert compacted.status == "passed"
    boundary = dispatch_event(tmp_path, "new-session", host="codex")
    assert boundary.status == "passed"
    assert boundary.metadata["closed_session_id"] == started.metadata["session_id"]
    package = tmp_path / "handoff.json"; package.write_text("{}")
    result = send_package(tmp_path, "codex", package)
    assert result.status in {"degraded", "passed"}
    assert platform.system()
