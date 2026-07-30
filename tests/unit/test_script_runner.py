import sys

import pytest

from framework_cli.scripts.runner import ScriptRunner


def test_runner_uses_argument_list_and_returns_status(tmp_path):
    result = ScriptRunner(tmp_path).run([sys.executable, "-c", "print('ok')"])
    assert result.returncode == 0
    assert result.stdout.strip() == "ok"


def test_runner_rejects_outside_workdir(tmp_path):
    with pytest.raises(PermissionError): ScriptRunner(tmp_path).run(["true"], cwd=tmp_path.parent)
