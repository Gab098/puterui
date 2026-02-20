"""Tests for configuration management."""

from pathlib import Path

from puterui.config import DEFAULT_MODEL, DEFAULT_OLLAMA_URL, Config


def test_default_config():
    """Config should have sensible defaults."""
    config = Config()
    assert config.ollama_url == DEFAULT_OLLAMA_URL
    assert config.model == DEFAULT_MODEL
    assert config.max_tokens == 4096
    assert config.temperature == 0.1
    assert config.max_iterations == 25
    assert isinstance(config.allowed_commands, list)
    assert "git" in config.allowed_commands


def test_config_load_defaults():
    """Config.load should return defaults when no config file exists."""
    config = Config.load(project_dir=Path("/nonexistent"))
    assert config.ollama_url == DEFAULT_OLLAMA_URL
    assert config.model == DEFAULT_MODEL


def test_config_env_override(monkeypatch):
    """Environment variables should override defaults."""
    monkeypatch.setenv("PUTERUI_OLLAMA_URL", "http://custom:1234")
    monkeypatch.setenv("PUTERUI_MODEL", "llama3:8b")
    config = Config.load(project_dir=Path("/nonexistent"))
    assert config.ollama_url == "http://custom:1234"
    assert config.model == "llama3:8b"


def test_config_load_from_file(tmp_path):
    """Config should load values from a TOML file."""
    config_file = tmp_path / "puterui.toml"
    config_file.write_text(
        'model = "codellama:13b"\n'
        "temperature = 0.5\n"
        "max_tokens = 2048\n"
    )
    config = Config.load(project_dir=tmp_path)
    assert config.model == "codellama:13b"
    assert config.temperature == 0.5
    assert config.max_tokens == 2048
