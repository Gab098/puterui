"""Tests for the Ollama client."""


from puterui.client import OllamaClient, _format_ollama_http_error
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


def test_format_ollama_http_error_401_signin_url() -> None:
    body = (
        '{"error":"unauthorized","signin_url":"https://ollama.com/connect?name=localhost"}'
    )
    msg = _format_ollama_http_error(401, body)
    assert "requires Ollama account authentication" in msg
    assert "https://ollama.com/connect?name=localhost" in msg


def test_format_ollama_http_error_json_message() -> None:
    body = '{"error":"model not found"}'
    msg = _format_ollama_http_error(404, body)
    assert msg == "Ollama API error (404): model not found"
