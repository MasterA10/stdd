import time

from framework_cli.quality.engine import QualityEngine


def test_scan_reference_codebase_completes(tmp_path):
    for index in range(25):
        (tmp_path / f"module_{index}.py").write_text(f"def f_{index}():\n    return {index}\n")
    started = time.monotonic()
    result = QualityEngine(tmp_path).run()
    assert time.monotonic() - started < 5
    assert result.exit_code == 0
