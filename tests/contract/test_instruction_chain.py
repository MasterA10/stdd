from framework_cli.agents.instructions import discover_instruction_chain


def test_nested_instruction_is_more_specific(tmp_path):
    (tmp_path / "AGENTS.md").write_text("root")
    (tmp_path / "src").mkdir()
    (tmp_path / "src/CLAUDE.md").write_text("specific")
    chain = discover_instruction_chain(tmp_path, tmp_path / "src")
    assert [x.path for x in chain.files] == ["AGENTS.md", "src/CLAUDE.md"]


def test_conflicting_instruction_stops_chain(tmp_path):
    (tmp_path / "AGENTS.md").write_text("<<<<<<< ours")
    assert not discover_instruction_chain(tmp_path).valid
