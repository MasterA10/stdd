from pathlib import Path

from looper import reviews


def test_review_config_migrates_terminal_mode_to_herdr(tmp_path: Path):
    """Configurações antigas não podem manter execução direta de subagentes.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    config = tmp_path / ".looper/config.yaml"
    config.parent.mkdir()
    config.write_text("review:\n  execution_mode: terminal\n", encoding="utf-8")

    loaded = reviews.load_review_config(tmp_path)

    assert loaded["execution_mode"] == "herdr"


def test_run_agent_always_delegates_to_herdr(tmp_path: Path, monkeypatch):
    """Toda execução de revisão usa o executor isolado em herdr.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    calls = []

    def fake_herdr(command, root, timeout, review_id, prompt=""):
        """Registra a chamada simulada do executor herdr.
        Armazena os argumentos recebidos e retorna uma resposta determinística para o teste.
        """
        calls.append((command, root, timeout, review_id, prompt))
        return 0, "ok", ""

    monkeypatch.setattr(reviews, "_run_herdr", fake_herdr)

    result = reviews._run_agent({"execution_mode": "terminal"}, ["agy"], tmp_path, 30, "review-id", prompt="prompt test")

    assert result == (0, "ok", "")
    assert calls == [(["agy"], tmp_path, 30, "review-id", "prompt test")]
