import json

from framework_cli.reporting.models import CommandResult, Finding
from framework_cli.reporting.render import render


def test_json_envelope_and_text_share_finding():
    result = CommandResult("framework check")
    result.add(Finding("Q1", "complexity", "warning", "open", "app.py", 4, "long", "too long"))
    payload = json.loads(render(result, "json"))
    assert payload["schema_version"] == 1
    assert payload["findings"][0]["path"] == "app.py"
    assert "too long" in render(result)
