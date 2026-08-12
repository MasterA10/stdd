import json
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from stdd.cli import app


runner = CliRunner()


def test_setup_discovers_nested_javascript_project(tmp_path: Path):
    """Descobre package.json em subprojeto.
    Ignora artefatos internos do monorepo.
    """
    (tmp_path / "packages/web").mkdir(parents=True)
    (tmp_path / "packages/web/package.json").write_text('{"devDependencies":{"typescript":"6.0.0"}}')
    (tmp_path / "node_modules/ignored").mkdir(parents=True)
    (tmp_path / "node_modules/ignored/package.json").write_text('{"dependencies":{"react":"latest"}}')

    result = runner.invoke(app, ["setup", str(tmp_path)])

    assert result.exit_code == 0
    config = json.loads((tmp_path / ".stdd/config.json").read_text())
    assert config["stack"]["languages"] == ["typescript"]
    assert "node_modules" not in json.dumps(config["stack"]["evidence"])


def test_static_dispatcher_reports_python_symbols_and_contract(tmp_path: Path):
    """Executa o dispatcher local e retorna contrato.
    Confirma símbolo e métrica Python determinísticos.
    """
    source = tmp_path / "src/service.py"
    source.parent.mkdir()
    source.write_text("def create_order(value):\n    if value:\n        return value\n    return None\n")
    adapter = Path(__file__).parents[1] / "src/stdd/templates/adapters/static_adapter.py"
    request = {"contract_version": "1", "project_path": str(tmp_path), "changed_files": [], "mode": "full"}

    process = subprocess.run(["python3", str(adapter)], cwd=tmp_path, input=json.dumps(request), text=True, capture_output=True)
    report = json.loads(process.stdout)

    assert process.returncode == 0
    assert report["contract_version"] == "1"
    assert any(item["qualified_name"].endswith("service.create_order") for item in report["symbols"])
    assert any(item["cyclomatic"] == 2 for item in report["complexity"])


def test_setup_keeps_php_direct_adapter_for_php_only_project(tmp_path: Path):
    """Mantém o adapter PHP nativo.
    Aplica a regra para projeto PHP isolado.
    """
    (tmp_path / "src/Service.php").parent.mkdir()
    (tmp_path / "src/Service.php").write_text("<?php function create_order($value) { return $value; }")

    result = runner.invoke(app, ["setup", str(tmp_path)])

    assert result.exit_code == 0
    config = json.loads((tmp_path / ".stdd/config.json").read_text())
    assert config["static_analysis"]["adapter_command"] == ["php", ".stdd/adapters/php_static_adapter.php"]
