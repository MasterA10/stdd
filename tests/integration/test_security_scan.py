from framework_cli.security.scanner import SecurityScanner


def test_security_redacts_and_blocks_provider_token(tmp_path):
    sample_value = "gh" + "p_123456789012345678901234567890"
    assignment = "TOKE" + "N = '" + sample_value + "'\n"
    (tmp_path / "app.py").write_text(assignment)
    result = SecurityScanner(tmp_path).scan()
    assert result.exit_code == 1
    text = str(result.to_dict())
    assert "ghp_" not in text


def test_example_placeholder_is_allowed(tmp_path):
    example = "API_" + "KEY=your-key-here\n"
    (tmp_path / ".env.example").write_text(example)
    assert SecurityScanner(tmp_path).scan().exit_code == 0
