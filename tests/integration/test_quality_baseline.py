import json

from framework_cli.quality.engine import QualityEngine


def test_baseline_changes_block_to_warning(tmp_path):
    (tmp_path / "bad.py").write_text("def long():\n" + "    x = 1\n" * 55)
    first = QualityEngine(tmp_path).run().findings
    fp = first[0].fingerprint
    baseline = tmp_path / ".framework/quality/baseline.json"
    baseline.parent.mkdir(parents=True)
    baseline.write_text(json.dumps({"findings": [{"fingerprint": fp}]}))
    second = QualityEngine(tmp_path).run().findings
    assert any(x.status == "baseline" and x.severity == "warning" for x in second)
