from framework_cli.config.loader import save_config
from framework_cli.config.model import ProjectConfig
from framework_cli.learn.handoff import export_package, import_package
from framework_cli.learn.lifecycle import start


def enabled(tmp_path):
    config = ProjectConfig.default(tmp_path); config.learn["enabled"] = True; save_config(tmp_path, config)


def test_handoff_import_rejects_markdown_parity_changes_and_duplicate_import(tmp_path):
    enabled(tmp_path); start(tmp_path); exported = export_package(tmp_path)
    package = next((tmp_path / ".framework/learn/handoffs").glob("*/handoff.json"))
    package.with_name("handoff.md").write_text(package.with_name("handoff.md").read_text() + "\nchanged\n")
    assert import_package(tmp_path, package).status == "blocked"
    package.with_name("handoff.md").write_text(export_package(tmp_path).metadata.get("markdown", "") or "")
    # Re-exporting creates a valid package; importing it twice is idempotently rejected.
    valid = next(path for path in (tmp_path / ".framework/learn/handoffs").glob("*/handoff.json") if path != package)
    assert import_package(tmp_path, valid).status == "passed"
    assert import_package(tmp_path, valid).status == "error"
