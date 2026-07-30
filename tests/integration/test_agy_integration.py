import json

from framework_cli.agents.projections import install_projections, integration_status
from framework_cli.commands.install import install
from framework_cli.commands.workflow import _configured_command


def test_agy_projection_uses_local_skills_layout(tmp_path):
    result = install(tmp_path, "agy")

    assert result.exit_code == 0
    skill = tmp_path / ".agents/skills/framework-check/SKILL.md"
    assert skill.exists()
    assert "name: framework-check" in skill.read_text()
    state = json.loads((tmp_path / ".framework/agents/integration.json").read_text())
    assert state["installed_integrations"] == ["agy"]
    assert integration_status(tmp_path)["modified"] == []


def test_agy_and_codex_shared_skills_root_is_not_installed_together(tmp_path):
    install_projections(tmp_path, ["codex"])

    result = install(tmp_path, "agy")

    assert result.exit_code == 4
    assert any(item.startswith("incompatible:") for item in result.metadata["conflicts"])


def test_installed_agy_becomes_the_default_local_workflow_agent(tmp_path, monkeypatch):
    install(tmp_path, "agy")
    monkeypatch.setattr("framework_cli.commands.workflow.shutil.which",
                        lambda name: "/usr/local/bin/agy" if name == "agy" else None)

    command = _configured_command(tmp_path, None)

    assert command == (["/usr/local/bin/agy", "--print"], False)
