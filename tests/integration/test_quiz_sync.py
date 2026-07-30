from framework_cli.config.loader import save_config
from framework_cli.config.model import ProjectConfig
from framework_cli.commands.quiz import generate
from framework_cli.learn.lifecycle import start
from framework_cli.quiz.sync import sync_quiz


def test_quiz_sync_marks_changed_sources_without_deleting_questions(tmp_path):
    config = ProjectConfig.default(tmp_path); config.learn["enabled"] = True; save_config(tmp_path, config)
    source = tmp_path / "app.py"; source.write_text("def stable_boundary():\n    return True\n")
    start(tmp_path); generated = generate(tmp_path, agent="local")
    assert generated.metadata["count"] == 1
    source.write_text("def stable_boundary():\n    return False\n")
    synced = sync_quiz(tmp_path)
    assert synced.metadata["needs_review"]
    assert list((tmp_path / ".framework/learn/quiz/questions").glob("*.json"))
