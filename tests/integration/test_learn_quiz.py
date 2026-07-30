from framework_cli.config.loader import save_config
from framework_cli.config.model import ProjectConfig
from framework_cli.commands.quiz import generate
from framework_cli.learn.lifecycle import start
from framework_cli.quiz.runner import run_quiz
from framework_cli.quiz.sync import sync_quiz


def test_local_quiz_can_run_without_agent_command(tmp_path):
    config = ProjectConfig.default(tmp_path); config.learn["enabled"] = True; save_config(tmp_path, config)
    (tmp_path / "app.py").write_text("def stable_boundary():\n    return True\n")
    start(tmp_path)
    generated = generate(tmp_path, agent="local")
    assert generated.metadata["agent"] == "local"
    quiz = run_quiz(tmp_path, count=1)
    assert quiz.exit_code == 0
    assert quiz.metadata["questions"]
    synced = sync_quiz(tmp_path)
    assert synced.exit_code == 0


def test_quiz_can_delegate_to_a_local_agent_executable(tmp_path):
    config = ProjectConfig.default(tmp_path); config.learn["enabled"] = True
    command = tmp_path / "agent-command.sh"
    command.write_text("#!/bin/sh\nprintf '%s' '{\"status\":\"completed\",\"questions\":[]}'\n")
    command.chmod(0o755); config.learn["agents"] = {"codex": {"command": str(command)}}; save_config(tmp_path, config)
    start(tmp_path)
    result = generate(tmp_path, agent="codex")
    assert result.metadata["status"] in {"completed", "partial"}
    assert set(result.metadata) == {"status", "job_id"}
