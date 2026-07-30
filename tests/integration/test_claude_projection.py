from framework_cli.agents.projections import install_projections


def test_claude_projection_is_native_command_file(tmp_path):
    install_projections(tmp_path, ["claude"])
    assert (tmp_path / ".claude/commands/framework-security-scan.md").exists()
