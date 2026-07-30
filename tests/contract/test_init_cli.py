import json

from framework_cli.cli import main


def test_init_noninteractive_requires_integration(tmp_path, capsys):
    assert main(["init", str(tmp_path), "--non-interactive", "--format", "json"]) == 2
    assert "integration" in capsys.readouterr().out.lower()


def test_init_creates_profile(tmp_path, capsys):
    assert main(["init", str(tmp_path), "--non-interactive", "--integration", "codex", "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert (tmp_path / ".framework/project.yml").exists()
    assert data["project"]["agent"]["integrations"][0]["id"] == "codex"
