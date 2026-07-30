from framework_cli.agents.projections import install_projections


def test_projection_does_not_overwrite_local_modification(tmp_path):
    install_projections(tmp_path, ["codex"])
    target = tmp_path / ".agents/skills/framework-check/SKILL.md"
    target.write_text("local change")
    data = install_projections(tmp_path, ["codex"])
    assert str(target.relative_to(tmp_path)) in data["conflicts"]
    assert target.read_text() == "local change"
