import builtins

from framework_cli.commands.init import init_project
from framework_cli.config.loader import load_config


def test_guided_greenfield_initialization_persists_answers(tmp_path, monkeypatch):
    answers = iter(["python", "fastapi", "postgresql", "pytest", "product", "codex", "S"])
    monkeypatch.setattr(builtins, "input", lambda _: next(answers))

    result = init_project(tmp_path, interactive=True)

    assert result.exit_code == 0
    config = load_config(tmp_path)
    assert config.mode == "greenfield"
    assert config.profile == "product"
    assert config.applications["root"]["frameworks"] == ["fastapi"]
    assert (tmp_path / ".framework" / "agents" / "requests").is_dir()
