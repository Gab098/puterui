"""Ollama API client for PuterUI."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from puterui.config import Config


class OllamaError(Exception):
    """Raised when the Ollama API returns an error."""

def _format_ollama_http_error(status_code: int, body: str) -> str:
    """Format Ollama HTTP errors into actionable messages."""
    message = f"Ollama API error ({status_code})"

    parsed: dict[str, Any] | None = None
    try:
        candidate = json.loads(body)
        if isinstance(candidate, dict):
            parsed = candidate
    except Exception:
        parsed = None

    if parsed is None:
        snippet = body.strip()
        if snippet:
            return f"{message}: {snippet}"
        return message

    err = str(parsed.get("error", "")).strip()
    signin_url = str(parsed.get("signin_url", "")).strip()

    if status_code == 401 and signin_url:
        detail = err or "unauthorized"
        return (
            f"{message}: {detail}.\n"
            "This model/provider requires Ollama account authentication.\n"
            f"Sign in by opening: {signin_url}"
        )

    if err:
        return f"{message}: {err}"

    return f"{message}: {body.strip()}"


class OllamaClient:
    """Lightweight async client for the Ollama chat API."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.base_url = config.ollama_url.rstrip("/")
        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0),
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def list_models(self) -> list[dict[str, Any]]:
        """List locally available models."""
        try:
            resp = await self._http.get("/api/tags")
            resp.raise_for_status()
            return resp.json().get("models", [])
        except httpx.HTTPError as exc:
            raise OllamaError(f"Failed to list models: {exc}") from exc

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Send a chat completion request (non-streaming) with optional tool definitions."""
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }
        if tools:
            payload["tools"] = tools

        try:
            resp = await self._http.post("/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            msg = _format_ollama_http_error(exc.response.status_code, body)
            raise OllamaError(msg) from exc
        except httpx.HTTPError as exc:
            raise OllamaError(f"Connection error: {exc}") from exc

    async def chat_stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream a chat completion response."""
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }
        if tools:
            payload["tools"] = tools

        try:
            async with self._http.stream("POST", "/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.strip():
                        yield json.loads(line)
        except httpx.HTTPStatusError as exc:
            body = exc.response.text
            msg = _format_ollama_http_error(exc.response.status_code, body)
            raise OllamaError(msg) from exc
        except httpx.HTTPError as exc:
            raise OllamaError(f"Connection error: {exc}") from exc

    async def check_health(self) -> bool:
        """Check if Ollama is reachable."""
        try:
            resp = await self._http.get("/")
            return resp.status_code == 200
        except httpx.HTTPError:
            return False
