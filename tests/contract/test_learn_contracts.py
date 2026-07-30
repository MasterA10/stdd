import json

from framework_cli.config.loader import save_config
from framework_cli.config.model import ProjectConfig
from framework_cli.learn.handoff import export_package, import_package
from framework_cli.learn.lifecycle import start
from framework_cli.commands.quiz import generate


def enabled(tmp_path):
    config = ProjectConfig.default(tmp_path)
    config.learn["enabled"] = True
    save_config(tmp_path, config)


def test_handoff_has_structured_and_markdown_views_and_links_new_session(tmp_path):
    enabled(tmp_path); first = start(tmp_path)
    package_result = export_package(tmp_path)
    assert package_result.status == "passed"
    package = next((tmp_path / ".framework" / "learn" / "handoffs").glob("*/handoff.json"))
    assert package.with_name("handoff.md").exists()
    imported = import_package(tmp_path, package)
    assert imported.status == "passed"
    assert imported.metadata["source_session_id"] == first.metadata["session_id"]
    assert imported.metadata["session"]["parent_session_id"] == first.metadata["session_id"]


def test_command_quiz_returns_ack_only(tmp_path):
    enabled(tmp_path); start(tmp_path)
    result = generate(tmp_path, agent="codex")
    assert set(result.metadata) == {"status", "job_id"}
    assert result.metadata["job_id"].startswith("job-")


def test_command_questions_are_stored_behind_ack_boundary(tmp_path):
    enabled(tmp_path); start(tmp_path)
    def provider(request):
        return {"status": "completed", "job_id": request["job_id"], "questions": [{
            "question_id": "question-external", "category": "trade-off", "prompt": "Which choice is explicit?",
            "options": ["A", "B", "C"], "correct_option": "A", "explanation": "It preserves the boundary.",
            "sources": [{"kind": "decision", "id": "plan.md", "fingerprint": "sha256:fixture"}],
            "provenance": {"command": "codex", "job_id": request["job_id"], "version": "1", "scope": {}}}]}
    result = __import__("framework_cli.commands.quiz", fromlist=["generate"]).generate(tmp_path, agent="codex", command_callback=provider)
    assert set(result.metadata) == {"status", "job_id"}
    assert (tmp_path / ".framework" / "learn" / "quiz" / "questions" / "question-external-v1.json").exists()
