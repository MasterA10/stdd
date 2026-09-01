from pathlib import Path

from looper import reviews


def test_review_config_migrates_terminal_mode_to_tmux(tmp_path: Path):
    """Configurações antigas não podem manter execução direta de subagentes."""
    config = tmp_path / ".looper/config.yaml"
    config.parent.mkdir()
    config.write_text("review:\n  execution_mode: terminal\n", encoding="utf-8")

    loaded = reviews.load_review_config(tmp_path)

    assert loaded["execution_mode"] == "tmux"


def test_run_agent_always_delegates_to_tmux(tmp_path: Path, monkeypatch):
    """Toda execução de revisão usa o executor isolado em tmux."""
    calls = []

    def fake_tmux(command, root, timeout, review_id):
        calls.append((command, root, timeout, review_id))
        return 0, "ok", ""

    monkeypatch.setattr(reviews, "_run_tmux", fake_tmux)

    result = reviews._run_agent({"execution_mode": "terminal"}, ["agy"], tmp_path, 30, "review-id")

    assert result == (0, "ok", "")
    assert calls == [(["agy"], tmp_path, 30, "review-id")]
