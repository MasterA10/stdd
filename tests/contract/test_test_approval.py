from framework_cli.config.loader import save_config
from framework_cli.config.model import ProjectConfig
from framework_cli.testing.approval import approval_findings, approve_test


def _project(tmp_path, profile="mvp"):
    config = ProjectConfig.default(tmp_path)
    config.profile = profile
    save_config(tmp_path, config)
    test = tmp_path / "tests" / "test_behavior.py"
    test.parent.mkdir(exist_ok=True)
    test.write_text("def test_behavior():\n    assert True\n")
    return test


def test_approval_hash_blocks_modified_test_in_mvp(tmp_path):
    test = _project(tmp_path)
    assert approve_test(tmp_path, "tests/test_behavior.py").exit_code == 0

    test.write_text("def test_behavior():\n    assert False\n")

    findings = approval_findings(tmp_path)
    assert len(findings) == 1
    assert findings[0].severity == "block"
    assert findings[0].rule == "approved-test-modified"


def test_experiment_profile_warns_instead_of_blocking(tmp_path):
    test = _project(tmp_path, profile="experiment")
    approve_test(tmp_path, "tests/test_behavior.py")
    test.write_text("def test_behavior():\n    assert False\n")

    assert approval_findings(tmp_path)[0].severity == "warning"
