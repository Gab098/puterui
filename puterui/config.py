"""Configuration management for PuterUI."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


CONFIG_FILENAME = "puterui.toml"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5-coder:7b"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.1
DEFAULT_MAX_ITERATIONS = 25


@dataclass
class Config:
    """Application configuration."""

    ollama_url: str = DEFAULT_OLLAMA_URL
    model: str = DEFAULT_MODEL
    max_tokens: int = DEFAULT_MAX_TOKENS
    temperature: float = DEFAULT_TEMPERATURE
    max_iterations: int = DEFAULT_MAX_ITERATIONS
    system_prompt: str = ""
    allowed_commands: list[str] = field(default_factory=lambda: [
        "ls", "cat", "head", "tail", "find", "grep", "wc",
        "git", "python", "pip", "npm", "node", "cargo", "go",
        "make", "echo", "pwd", "whoami", "date", "uname",
    ])

    @classmethod
    def load(cls, project_dir: Path | None = None) -> Config:
        """Load config from file, falling back to defaults."""
        config = cls()

        # Check env overrides first
        if url := os.environ.get("PUTERUI_OLLAMA_URL"):
            config.ollama_url = url
        if model := os.environ.get("PUTERUI_MODEL"):
            config.model = model

        # Try loading from project-level config
        search_dirs = []
        if project_dir:
            search_dirs.append(project_dir)
        search_dirs.append(Path.cwd())
        search_dirs.append(Path.home() / ".config" / "puterui")

        for d in search_dirs:
            config_path = d / CONFIG_FILENAME
            if config_path.exists():
                config._load_from_file(config_path)
                break

        return config

    def _load_from_file(self, path: Path) -> None:
        """Load settings from a TOML config file."""
        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
        except Exception:
            return

        if "ollama_url" in data:
            self.ollama_url = str(data["ollama_url"])
        if "model" in data:
            self.model = str(data["model"])
        if "max_tokens" in data:
            self.max_tokens = int(data["max_tokens"])
        if "temperature" in data:
            self.temperature = float(data["temperature"])
        if "max_iterations" in data:
            self.max_iterations = int(data["max_iterations"])
        if "system_prompt" in data:
            self.system_prompt = str(data["system_prompt"])
        if "allowed_commands" in data:
            self.allowed_commands = list(data["allowed_commands"])
