from framework_cli.testing.explanations import explain_test, sync_explanations


def _fixture(tmp_path):
    (tmp_path / "app.py").write_text(
        "def calculate_total(value: int) -> int:\n"
        "    \"\"\"Returns the bounded total.\"\"\"\n"
        "    return max(value, 0)\n"
    )
    test = tmp_path / "tests" / "test_total.py"
    test.parent.mkdir()
    test.write_text("from app import calculate_total\n\n\ndef test_total():\n    assert calculate_total(-1) == 0\n")
    return test


def test_explain_python_test_generates_resolved_symbol_header(tmp_path):
    test = _fixture(tmp_path)

    result = explain_test(tmp_path, "tests/test_total.py")

    content = test.read_text()
    assert result.exit_code == 0
    assert "@framework:explanations:start" in content
    assert "calculate_total(value: int) -> int" in content
    assert "Returns the bounded total." in content
    assert "Fonte: app.py" in content


def test_sync_updates_signature_and_removes_stale_generated_block(tmp_path):
    test = _fixture(tmp_path)
    explain_test(tmp_path, "tests/test_total.py")
    (tmp_path / "app.py").write_text("def calculate_total(value: int, floor: int = 0) -> int:\n    return max(value, floor)\n")

    result = sync_explanations(tmp_path)

    assert result.exit_code == 0
    content = test.read_text()
    assert "floor: int=0" in content
    assert content.count("@framework:explanations:start") == 1


def test_virtual_mode_does_not_modify_test(tmp_path):
    test = _fixture(tmp_path)
    original = test.read_text()

    result = explain_test(tmp_path, "tests/test_total.py", mode="virtual")

    assert result.metadata["mode"] == "virtual"
    assert result.metadata["changed"] is False
    assert test.read_text() == original


def test_sync_updates_full_source_symbol_index(tmp_path):
    _fixture(tmp_path)

    result = sync_explanations(tmp_path)

    assert result.metadata["indexed_symbols"]
    from framework_cli.index.db import IndexDB

    db = IndexDB(tmp_path / ".framework" / "index.db")
    row = db.connection.execute("select path, name from symbols where name='calculate_total'").fetchone()
    db.close()
    assert tuple(row) == ("app.py", "calculate_total")


def test_sync_without_markers_can_explain_all_tests(tmp_path):
    test = _fixture(tmp_path)

    result = sync_explanations(tmp_path, include_unmarked=True)

    assert result.exit_code == 0
    assert str(test.relative_to(tmp_path)) in result.metadata["updated"]
