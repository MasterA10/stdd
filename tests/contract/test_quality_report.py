import json

from framework_cli.reporting.render import render
from framework_cli.security.scanner import SecurityScanner


def test_security_report_has_no_secret_value(tmp_path):
    sample_value = "gh" + "p_123456789012345678901234567890"
    assignment = "API_" + "KEY = '" + sample_value + "'"
    (tmp_path / "x.py").write_text(assignment)
    result = SecurityScanner(tmp_path).scan()
    assert sample_value not in render(result)
    assert sample_value not in json.dumps(result.to_dict())
