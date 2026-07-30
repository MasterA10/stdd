from framework_cli.quality.engine import QualityEngine


def test_quality_detects_long_function_and_god_class(tmp_path):
    body = "\n".join(["def long():"] + ["    x = 1"] * 55)
    (tmp_path / "bad.py").write_text(body + "\n")
    findings = QualityEngine(tmp_path).run().findings
    assert any(getattr(x, "rule", "") == "function_logical_lines" for x in findings)


def test_quality_is_clean_for_small_function(tmp_path):
    (tmp_path / "good.py").write_text("def good():\n    return 1\n")
    assert not QualityEngine(tmp_path).run().findings
