"""Persona / Soul system for PuterUI.

Inspired by OpenClaw's identity concept -- the assistant has a configurable
personality, communication style, and set of values that shape how it
interacts with the user.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


PERSONA_FILENAME = "persona.toml"
BUILTIN_PERSONAS_DIR = Path(__file__).parent / "builtin_personas"

DEFAULT_PERSONA = {
    "name": "Puter",
    "role": "AI coding assistant",
    "traits": [
        "concise and direct",
        "technically precise",
        "helpful but not overly eager",
        "admits uncertainty honestly",
    ],
    "communication_style": "casual-professional",
    "values": [
        "code quality over speed",
        "explain reasoning when asked",
        "respect the user's existing patterns",
        "safety first with destructive operations",
    ],
    "quirks": [],
    "backstory": "",
    "rules": [
        "Never make changes without explaining what you are doing",
        "Always read files before editing them",
        "Ask for confirmation before destructive operations",
    ],
}


@dataclass
class Persona:
    """Represents the assistant's identity and personality."""

    name: str = "Puter"
    role: str = "AI coding assistant"
    traits: list[str] = field(default_factory=lambda: list(DEFAULT_PERSONA["traits"]))
    communication_style: str = "casual-professional"
    values: list[str] = field(default_factory=lambda: list(DEFAULT_PERSONA["values"]))
    quirks: list[str] = field(default_factory=list)
    backstory: str = ""
    rules: list[str] = field(default_factory=lambda: list(DEFAULT_PERSONA["rules"]))

    def to_system_prompt(self) -> str:
        """Generate a system prompt section from this persona."""
        parts = [
            f"Your name is {self.name}. You are a {self.role}.",
        ]

        if self.backstory:
            parts.append(f"\nBackground: {self.backstory}")

        if self.traits:
            traits_str = ", ".join(self.traits)
            parts.append(f"\nPersonality: {traits_str}.")

        if self.communication_style:
            parts.append(f"Communication style: {self.communication_style}.")

        if self.values:
            parts.append("\nValues:")
            for v in self.values:
                parts.append(f"  - {v}")

        if self.rules:
            parts.append("\nRules you must follow:")
            for r in self.rules:
                parts.append(f"  - {r}")

        if self.quirks:
            parts.append("\nQuirks:")
            for q in self.quirks:
                parts.append(f"  - {q}")

        return "\n".join(parts)

    @classmethod
    def load(cls, project_dir: Optional[Path] = None) -> Persona:
        """Load persona from a TOML file, falling back to defaults."""
        persona = cls()

        search_dirs: list[Path] = []
        if project_dir:
            search_dirs.append(project_dir)
        search_dirs.append(Path.cwd())
        search_dirs.append(Path.home() / ".config" / "puterui")

        for d in search_dirs:
            persona_path = d / PERSONA_FILENAME
            if persona_path.exists():
                persona._load_from_file(persona_path)
                break

        return persona

    def _load_from_file(self, path: Path) -> None:
        """Load persona settings from a TOML file."""
        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
        except Exception:
            return

        if "name" in data:
            self.name = str(data["name"])
        if "role" in data:
            self.role = str(data["role"])
        if "traits" in data:
            self.traits = list(data["traits"])
        if "communication_style" in data:
            self.communication_style = str(data["communication_style"])
        if "values" in data:
            self.values = list(data["values"])
        if "quirks" in data:
            self.quirks = list(data["quirks"])
        if "backstory" in data:
            self.backstory = str(data["backstory"])
        if "rules" in data:
            self.rules = list(data["rules"])

    def summary(self) -> str:
        """Return a short summary of the persona for display."""
        traits = ", ".join(self.traits[:3])
        return f"{self.name} ({self.role}) -- {traits}"

    @classmethod
    def load_builtin(cls, name: str) -> Optional["Persona"]:
        """Load a built-in persona by name (e.g. 'hacker', 'osint-analyst')."""
        if not BUILTIN_PERSONAS_DIR.is_dir():
            return None

        # Try exact match first, then with .toml extension
        candidates = [
            BUILTIN_PERSONAS_DIR / name,
            BUILTIN_PERSONAS_DIR / f"{name}.toml",
        ]
        for path in candidates:
            if path.exists() and path.is_file():
                persona = cls()
                persona._load_from_file(path)
                return persona
        return None

    @classmethod
    def list_builtins(cls) -> list[str]:
        """List available built-in persona names."""
        if not BUILTIN_PERSONAS_DIR.is_dir():
            return []
        return sorted(
            p.stem for p in BUILTIN_PERSONAS_DIR.iterdir()
            if p.suffix == ".toml"
        )
