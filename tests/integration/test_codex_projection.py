import json

from framework_cli.agents.projections import install_projections


def test_codex_projection_has_manifest_checksum(tmp_path):
    data = install_projections(tmp_path, ["codex"])
    assert (tmp_path / ".agents/skills/framework-check/SKILL.md").exists()
    manifest = json.loads((tmp_path / data["manifest"]).read_text())
    assert manifest["projections"][0]["agent"] == "codex"
    assert manifest["projections"][0]["checksum"].startswith("sha256:")
