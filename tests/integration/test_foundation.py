from framework_cli.agents.instructions import discover_instruction_chain
from framework_cli.git.repository import GitRepository


def test_instruction_chain_and_git_degraded_mode(tmp_path):
    (tmp_path / "AGENTS.md").write_text("root")
    chain = discover_instruction_chain(tmp_path)
    assert [x.path for x in chain.files] == ["AGENTS.md"]
    assert GitRepository(tmp_path).available is False
