import os
import sys

from framework_cli.scripts.runner import ScriptRunner


def test_platform_runner_handles_paths_and_executable(tmp_path):
    result = ScriptRunner(tmp_path).run([sys.executable, "-c", "import os; print(os.getcwd())"])
    assert result.returncode == 0
    assert os.fspath(tmp_path) in result.stdout
