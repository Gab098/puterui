"""Tests for the Ollama client."""

import httpx

from puterui.client import OllamaClient, _format_http_error
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


def test_format_http_error_with_empty_message():
    """Formatter should return exception class when message is empty."""
    exc = httpx.ConnectError("")
    assert _format_http_error(exc) == "ConnectError"


def test_format_http_error_with_message():
    """Formatter should preserve normal exception messages."""
    exc = httpx.ConnectError("boom")
    assert _format_http_error(exc) == "boom"
