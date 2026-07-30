from pathlib import Path

import pytest

from framework_cli.config.loader import load_config, save_config
from framework_cli.config.model import ProjectConfig
from framework_cli.config.validator import validate_config


def test_config_round_trip(tmp_path):
    config = ProjectConfig.default(tmp_path)
    config.agent_integrations = ["codex"]
    save_config(tmp_path, config)
    loaded = load_config(tmp_path)
    assert loaded.profile == "mvp"
    assert loaded.agent_integrations == ["codex"]


def test_config_rejects_invalid_profile(tmp_path):
    config = ProjectConfig.default(tmp_path)
    config.profile = "invalid"
    with pytest.raises(ValueError): validate_config(config)


def test_config_rejects_path_escape(tmp_path):
    config = ProjectConfig.default(tmp_path)
    config.applications = {"escape": {"path": "../outside"}}
    with pytest.raises(ValueError): validate_config(config)


def test_unknown_config_key_is_reported(tmp_path):
    assert "unknown configuration key: future" in validate_config({"profile": "mvp", "future": True}, tmp_path)
