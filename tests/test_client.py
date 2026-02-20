"""Tests for the Ollama client."""


from puterui.client import OllamaClient
from puterui.config import Config


def test_client_init():
    """Client should initialize with config values."""
    config = Config(ollama_url="http://test:1234", model="test-model")
    client = OllamaClient(config)
    assert client.base_url == "http://test:1234"
    assert client.config.model == "test-model"


def test_client_strips_trailing_slash():
    """Client should strip trailing slash from URL."""
    config = Config(ollama_url="http://test:1234/")
    client = OllamaClient(config)
    assert client.base_url == "http://test:1234"
