from pathlib import Path

import yaml

from looper.config import DEFAULT_BACKEND_LOGGING_INSTRUCTION, config_path, instructions_for, load_config
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
    assert data["instructions"] == {"backend": DEFAULT_BACKEND_LOGGING_INSTRUCTION, "frontend": "", "change": ""}
    assert "Evite arquivos de back-end com mais de 300 linhas" in DEFAULT_BACKEND_LOGGING_INSTRUCTION
    assert "não um limite ou validação estática" in DEFAULT_BACKEND_LOGGING_INSTRUCTION


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
    assert isinstance(data["instructions"], dict)
    assert "Regra durável." in data["instructions"]["backend"]
    assert DEFAULT_BACKEND_LOGGING_INSTRUCTION in data["instructions"]["backend"]
    assert data["instructions"]["frontend"] == ""
    assert data["instructions"]["change"] == ""
    assert config_path(tmp_path).exists()
    assert not (looper / "config.json").exists()


def test_legacy_yaml_instructions_string_is_migrated_with_logging(tmp_path: Path):
    """Migra instructions em string no YAML para dict com a diretiva de logging.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    looper = tmp_path / ".looper"
    looper.mkdir()
    (looper / "config.yaml").write_text(
        "instructions: 'Regra existente no yaml.'\nversion: 1\n",
        encoding="utf-8",
    )
    data = load_config(tmp_path)
    assert isinstance(data["instructions"], dict)
    assert "Regra existente no yaml." in data["instructions"]["backend"]
    assert DEFAULT_BACKEND_LOGGING_INSTRUCTION in data["instructions"]["backend"]


def test_instructions_for_retorna_valor_da_fase_correta():
    """instructions_for retorna a instrução da fase solicitada no objeto estruturado.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    data = {"instructions": {"backend": "Log obrigatório.", "frontend": "Acessibilidade.", "change": "Revisão."}}
    assert instructions_for(data, "backend") == "Log obrigatório."
    assert instructions_for(data, "frontend") == "Acessibilidade."
    assert instructions_for(data, "change") == "Revisão."


def test_instructions_for_usa_backend_como_fallback_para_fases_sem_mapeamento():
    """Fases como 'test' e 'bootstrap' usam a instrução 'backend' como fallback.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    data = {"instructions": {"backend": "Instrução de backend.", "frontend": "F.", "change": "C."}}
    assert instructions_for(data, "test") == "Instrução de backend."
    assert instructions_for(data, "bootstrap") == "Instrução de backend."
    assert instructions_for(data, None) == "Instrução de backend."


def test_instructions_for_retrocompatibilidade_com_string_legada():
    """String legada em instructions é retornada para qualquer fase solicitada.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    data = {"instructions": "Regra global legada."}
    assert instructions_for(data, "backend") == "Regra global legada."
    assert instructions_for(data, "frontend") == "Regra global legada."
    assert instructions_for(data, "change") == "Regra global legada."
    assert instructions_for(data, None) == "Regra global legada."


def test_instructions_for_retorna_vazio_quando_fase_nao_preenchida():
    """instructions_for retorna string vazia quando o campo da fase está vazio.
    Verifica o comportamento usando as entradas, fixtures e asserções específicas do cenário.
    """
    data = {"instructions": {"backend": "", "frontend": "", "change": ""}}
    assert instructions_for(data, "backend") == ""
    assert instructions_for(data, "frontend") == ""
    assert instructions_for(data, "change") == ""
