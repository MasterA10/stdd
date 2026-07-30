from framework_cli.config.loader import save_config
from framework_cli.config.model import ProjectConfig
from framework_cli.commands.quiz import generate
from framework_cli.learn.lifecycle import start
from framework_cli.quiz.runner import run_quiz
from framework_cli.quiz.sync import sync_quiz


def test_local_quiz_can_run_without_external_provider(tmp_path):
    config = ProjectConfig.default(tmp_path); config.learn["enabled"] = True; save_config(tmp_path, config)
    (tmp_path / "app.py").write_text("def stable_boundary():\n    return True\n")
    start(tmp_path)
    generated = generate(tmp_path, provider="local")
    assert generated.metadata["provider"] == "local"
    quiz = run_quiz(tmp_path, count=1)
    assert quiz.exit_code == 0
    assert quiz.metadata["questions"]
    synced = sync_quiz(tmp_path)
    assert synced.exit_code == 0
