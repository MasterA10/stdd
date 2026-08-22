from pathlib import Path

import yaml

from looper.config import config_path, load_config
from looper.core import init_project


def test_init_creates_one_yaml_configuration_document(tmp_path: Path):
    """Cria a configuração consolidada em YAML.
    Confirma que revisão e instruções vivem no mesmo arquivo e que a TUI não é necessária.
    """
    init_project(tmp_path)
    assert config_path(tmp_path).exists()
    assert not (tmp_path / ".looper/config.json").exists()
    assert not (tmp_path / ".looper/review-agents.json").exists()
    assert not (tmp_path / ".looper/loop-instructions.md").exists()
    data = yaml.safe_load(config_path(tmp_path).read_text(encoding="utf-8"))
    assert isinstance(data["review"], dict)
    assert data["instructions"] == ""


def test_legacy_configuration_is_migrated_and_removed(tmp_path: Path):
    """Migra os documentos antigos sem perder dados desconhecidos.
    Inicializa um projeto legado e verifica o conteúdo consolidado no YAML.
    """
    looper = tmp_path / ".looper"
    looper.mkdir()
    (looper / "config.json").write_text('{"future_option":{"enabled":true}}', encoding="utf-8")
    (looper / "review-agents.json").write_text('{"enabled":true}', encoding="utf-8")
    (looper / "loop-instructions.md").write_text("Regra durável.", encoding="utf-8")
    data = load_config(tmp_path)
    assert data["future_option"]["enabled"] is True
    assert data["review"]["enabled"] is True
    assert data["instructions"] == "Regra durável."
    assert config_path(tmp_path).exists()
    assert not (looper / "config.json").exists()
