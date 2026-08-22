import json
from types import SimpleNamespace

from looper.core import init_project
from looper.draw import add_draw_change, create_draw, read_draw
from looper.reviews import ensure_review_workspace, run_review, set_review_enabled


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
    config = tmp_path / ".looper" / "review-agents.json"
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
    config_path = tmp_path / ".looper" / "review-agents.json"
    config = json.loads(config_path.read_text())
    config["enabled"] = True
    config["agents"]["codex"]["command"] = ["fake", "{model}", "{reasoning}", "{prompt}"]
    config_path.write_text(json.dumps(config))
    monkeypatch.setattr("looper.reviews.subprocess.run", lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="aprovado", stderr=""))
    result = run_review(tmp_path, {"id": "task:review-flow:node:1", "draw_id": "review-flow", "node_id": 1, "level": 2, "label": "Tela"})
    assert result["status"] == "approved"
    assert result["changes"] == []
    assert result["command"][1:3] == ["", "high"]


def test_review_detects_changes_created_by_agent(tmp_path, monkeypatch):
    init_project(tmp_path)
    _draw(tmp_path)
    config_path = tmp_path / ".looper" / "review-agents.json"
    config = json.loads(config_path.read_text())
    config["agents"]["codex"]["command"] = ["fake", "{prompt}"]
    config_path.write_text(json.dumps(config))

    def fake_run(*args, **kwargs):
        add_draw_change(tmp_path, "review-flow", 1, "Falta o estado de erro", metadata={"source": "review"})
        return SimpleNamespace(returncode=0, stdout="faltou", stderr="")

    monkeypatch.setattr("looper.reviews.subprocess.run", fake_run)
    result = run_review(tmp_path, {"id": "task:review-flow:node:1", "draw_id": "review-flow", "node_id": 1, "level": 2, "label": "Tela"})
    assert result["status"] == "changes_created"
    assert len(result["changes"]) == 1
    assert list((tmp_path / ".looper" / "reviews").glob("*.json"))


def test_review_can_be_disabled_without_calling_agent(tmp_path, monkeypatch):
    init_project(tmp_path)
    _draw(tmp_path)
    set_review_enabled(tmp_path, False)
    called = []
    monkeypatch.setattr("looper.reviews.subprocess.run", lambda *args, **kwargs: called.append(args))
    result = run_review(tmp_path, {"id": "task:review-flow:node:1", "draw_id": "review-flow", "node_id": 1, "level": 2, "label": "Tela"}, force=False)
    assert result["status"] == "skipped"
    assert called == []
