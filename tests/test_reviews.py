from types import SimpleNamespace

import yaml

from looper.core import init_project
from looper.draw import add_draw_change, create_draw, read_draw
from looper.reviews import ensure_review_workspace, maybe_review_completed_task, run_review, set_review_enabled


def _draw(root):
    create_draw(root, {
        "id": "review-flow",
        "title": "Review flow",
        "kind": "feature",
        "nodes": [
            {"id": 1, "label": "Tela", "symbol": "Tela"},
            {"id": 2, "label": "Fim", "symbol": "Fim"},
        ],
        "edges": [{"id": 1, "from": 1, "to": 2, "condition": 1}],
    })


def test_review_workspace_is_idempotent_and_preserves_config(tmp_path):
    init_project(tmp_path)
    config = tmp_path / ".looper" / "config.yaml"
    original = config.read_text()
    assert config.exists()
    assert (tmp_path / ".looper" / "reviews").is_dir()
    assert ensure_review_workspace(tmp_path) == []
    assert config.read_text() == original


def test_add_draw_change_creates_pending_change(tmp_path):
    _draw(tmp_path)
    created = add_draw_change(tmp_path, "review-flow", 1, "Validar estado vazio", metadata={"source": "review"})
    assert created["change"]["status"] == "pending"
    assert read_draw(tmp_path, "review-flow")["nodes"][0]["changes"][0]["source"] == "review"


def test_review_without_changes_means_approved(tmp_path, monkeypatch):
    init_project(tmp_path)
    _draw(tmp_path)
    config_path = tmp_path / ".looper" / "config.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["review"]["enabled"] = True
    config["review"]["default_agent"] = "codex"
    config["review"]["agents"]["codex"]["command"] = ["fake", "{model}", "{reasoning}", "{prompt}"]
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False))
    monkeypatch.setattr("looper.reviews.subprocess.run", lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="aprovado", stderr=""))
    result = run_review(tmp_path, {"id": "task:review-flow:node:1", "draw_id": "review-flow", "node_id": 1, "level": 2, "label": "Tela"})
    assert result["status"] == "approved"
    assert result["changes"] == []
    assert result["command"][1:3] == ["", "high"]


def test_review_detects_changes_created_by_agent(tmp_path, monkeypatch):
    init_project(tmp_path)
    _draw(tmp_path)
    config_path = tmp_path / ".looper" / "config.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["review"]["agents"]["codex"]["command"] = ["fake", "{prompt}"]
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False))

    def fake_run(*args, **kwargs):
        add_draw_change(tmp_path, "review-flow", 1, "Falta o estado de erro", metadata={"source": "review"})
        return SimpleNamespace(returncode=0, stdout="faltou", stderr="")

    monkeypatch.setattr("looper.reviews.subprocess.run", fake_run)
    result = run_review(tmp_path, {"id": "task:review-flow:node:1", "draw_id": "review-flow", "node_id": 1, "level": 2, "label": "Tela"})
    assert result["status"] == "changes_created"
    assert len(result["changes"]) == 1
    assert list((tmp_path / ".looper" / "reviews").glob("*.json"))


def test_review_defaults_to_agy(tmp_path):
    init_project(tmp_path)

    config = yaml.safe_load((tmp_path / ".looper" / "config.yaml").read_text())

    assert config["review"]["default_agent"] == "agy"


def test_review_can_be_disabled_without_calling_agent(tmp_path, monkeypatch):
    init_project(tmp_path)
    _draw(tmp_path)
    set_review_enabled(tmp_path, False)
    called = []
    monkeypatch.setattr("looper.reviews.subprocess.run", lambda *args, **kwargs: called.append(args))
    result = run_review(tmp_path, {"id": "task:review-flow:node:1", "draw_id": "review-flow", "node_id": 1, "level": 2, "label": "Tela"}, force=False)
    assert result["status"] == "skipped"
    assert called == []


def test_review_runs_after_configured_number_of_tasks(tmp_path, monkeypatch):
    init_project(tmp_path)
    _draw(tmp_path)
    config_path = tmp_path / ".looper" / "config.yaml"
    config = yaml.safe_load(config_path.read_text())
    config["review"]["enabled"] = True
    config["review"]["interval_tasks"] = 2
    config["review"]["agents"]["codex"]["command"] = ["fake", "{prompt}"]
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False))
    monkeypatch.setattr("looper.reviews.subprocess.run", lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="aprovado", stderr=""))
    task = {"id": "task:review-flow:node:1", "draw_id": "review-flow", "node_id": 1, "level": 2, "label": "Tela"}
    assert maybe_review_completed_task(tmp_path, {"status": "done", "phase": "implementation", "task": task}) is None
    result = maybe_review_completed_task(tmp_path, {"status": "done", "phase": "implementation", "task": {**task, "id": "task:review-flow:node:2", "node_id": 2, "label": "Fim"}})
    assert result is not None
    assert result["status"] == "approved"
    saved = yaml.safe_load(config_path.read_text())
    assert saved["review"]["completed_since_last_review"] == 0
