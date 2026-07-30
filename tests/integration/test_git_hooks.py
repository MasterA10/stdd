from framework_cli.git.hooks import install_hooks


def test_hooks_preserve_existing_hook(tmp_path):
    (tmp_path / ".git/hooks").mkdir(parents=True)
    (tmp_path / ".git/hooks/pre-commit").write_text("#!/bin/sh\necho existing\n")
    result = install_hooks(tmp_path)
    assert "pre-commit" not in " ".join(result["installed"])
    assert result["conflicts"]
