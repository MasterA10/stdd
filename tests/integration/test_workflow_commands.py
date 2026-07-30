import json

from framework_cli.commands.workflow import create_test, implement, tradeoff
from framework_cli.index.db import IndexDB
from framework_cli.testing.explanations import explain_test


def test_create_and_agent_request_respect_instruction_chain(tmp_path, monkeypatch):
    monkeypatch.setattr("framework_cli.commands.workflow.shutil.which", lambda _name: None)
    created = create_test(tmp_path, "A complete checkout feature must reject invalid coupons")
    assert created.exit_code == 0
    assert created.metadata["status"] == "prepared"
    request = next((tmp_path / ".framework/agents/requests").glob("*.json"))
    payload = json.loads(request.read_text())
    assert payload["operation"] == "test-create"
    assert payload["context"]["request_type"] == "complete_feature_description"
    assert "invalid coupons" in payload["context"]["description"]

    result = implement(tmp_path, None)

    assert result.exit_code == 0
    assert result.metadata["status"] == "prepared"
    requests = list((tmp_path / ".framework/agents/requests").glob("*.json"))
    assert len(requests) == 2
    assert all("stdout" not in item.read_text() for item in requests)


def test_test_create_registers_multiple_tests_from_specialized_agent(tmp_path, monkeypatch):
    def fake_agent(root, operation, context, command):
        assert operation == "test-create"
        assert "feature-level" in context["deliverables"][0]
        first = root / "tests" / "unit" / "test_coupon.py"
        second = root / "tests" / "integration" / "test_checkout_coupon.py"
        plan = root / context["test_plan_path"]
        plan.parent.mkdir(parents=True, exist_ok=True)
        plan.write_text("# Test plan\n\n- Validate coupon boundaries\n- Validate persistence\n")
        (root / context["checklist_path"]).write_text(
            "# Test quality checklist\n\n- [x] Scenarios cover boundary and persistence behavior\n")
        first.parent.mkdir(parents=True)
        second.parent.mkdir(parents=True)
        first.write_text("def test_coupon_boundary():\n    assert False\n")
        second.parent.mkdir(parents=True, exist_ok=True)
        second.write_text("def test_checkout_persists_coupon():\n    assert False\n")
        return {"status": "completed", "request_id": "request-test", "agent": "codex"}

    monkeypatch.setattr("framework_cli.commands.workflow._invoke_agent", fake_agent)
    result = create_test(tmp_path, "A checkout feature with coupon validation and persistence")

    assert result.status == "completed"
    assert result.metadata["test_count"] == 2
    manifest = tmp_path / result.metadata["feature_manifest"]
    assert manifest.exists()
    manifest_data = json.loads(manifest.read_text())
    assert manifest_data["tests"] == [
        "tests/integration/test_checkout_coupon.py",
        "tests/unit/test_coupon.py",
    ]
    assert manifest_data["test_plan"].startswith(".framework/quality/features/")


def test_implement_completed_agent_does_not_reference_missing_regression(tmp_path, monkeypatch):
    monkeypatch.setattr("framework_cli.commands.workflow._invoke_agent",
                        lambda *args, **kwargs: {"status": "completed", "request_id": "request-test"})
    monkeypatch.setattr("framework_cli.commands.workflow._attach_gates", lambda *args: None)

    result = implement(tmp_path, None)

    assert result.status == "completed"
    assert result.metadata["history_path"]


def test_implement_blocks_new_function_without_concise_summary(tmp_path, monkeypatch):
    def fake_agent(root, operation, context, command):
        assert operation == "implement"
        (root / "app.py").write_text("def calculate_total(items):\n    return sum(items)\n")
        return {"status": "completed", "request_id": "request-implementation"}

    monkeypatch.setattr("framework_cli.commands.workflow._invoke_agent", fake_agent)
    monkeypatch.setattr("framework_cli.commands.workflow._attach_gates", lambda *args: None)

    result = implement(tmp_path, None)

    assert result.status == "blocked"
    assert result.exit_code == 1
    assert result.metadata["function_documentation"]["missing"][0]["name"] == "calculate_total"
    db = IndexDB(tmp_path / ".framework" / "index.db")
    try:
        row = db.connection.execute(
            "SELECT data FROM symbols WHERE name=?", ("calculate_total",)
        ).fetchone()
    finally:
        db.close()
    assert row is not None
    assert json.loads(row["data"])["description"] == "Descrição não encontrada no código-fonte."


def test_implement_persists_concise_function_summary(tmp_path, monkeypatch):
    def fake_agent(root, operation, context, command):
        (root / "app.py").write_text(
            'def calculate_total(items):\n    """Soma os itens do pedido."""\n    return sum(items)\n'
        )
        return {"status": "completed", "request_id": "request-documented"}

    monkeypatch.setattr("framework_cli.commands.workflow._invoke_agent", fake_agent)
    monkeypatch.setattr("framework_cli.commands.workflow._attach_gates", lambda *args: None)

    result = implement(tmp_path, None)

    assert result.status == "completed"
    assert result.metadata["function_documentation"]["missing"] == []
    assert result.metadata["function_documentation"]["documented"][0]["summary"] == \
        "Soma os itens do pedido."


def test_agentic_command_is_blocked_by_instruction_conflict(tmp_path):
    (tmp_path / "AGENTS.md").write_text("CONFLICT: local instructions disagree\n")

    result = tradeoff(tmp_path, "sync or async processing")

    assert result.status == "blocked"
    assert result.exit_code == 1


def test_explain_all_only_updates_test_files(tmp_path):
    (tmp_path / "app.py").write_text("def value():\n    return 1\n")
    test = tmp_path / "tests/test_value.py"
    test.parent.mkdir()
    test.write_text("from app import value\n\ndef test_value():\n    assert value() == 1\n")

    result = explain_test(tmp_path, "tests/test_value.py", mode="first-use")

    assert result.metadata["symbols"][0]["name"] == "value"
    assert "@framework:explanations:start" in test.read_text()
