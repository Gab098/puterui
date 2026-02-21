"""Skills system for PuterUI.

Skills are loadable instruction modules (markdown or TOML files) that give
the assistant specialized knowledge for specific tasks like creating APIs,
writing tests, setting up CI/CD, etc.
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


SKILLS_DIR_NAME = "skills"
BUILTIN_SKILLS_DIR = Path(__file__).parent / "builtin_skills"


@dataclass
class Skill:
    """A single skill definition."""

    name: str
    description: str = ""
    instructions: str = ""
    tags: list[str] = field(default_factory=list)
    source_path: Optional[str] = None

    def to_prompt_section(self) -> str:
        """Format this skill as a system prompt injection."""
        parts = [f"\n--- Skill: {self.name} ---"]
        if self.description:
            parts.append(self.description)
        if self.instructions:
            parts.append(self.instructions)
        parts.append(f"--- End Skill: {self.name} ---\n")
        return "\n".join(parts)


class SkillRegistry:
    """Manages loading and activating skills."""

    def __init__(self) -> None:
        self._available: dict[str, Skill] = {}
        self._active: dict[str, Skill] = {}

    @property
    def available(self) -> dict[str, Skill]:
        return dict(self._available)

    @property
    def active(self) -> dict[str, Skill]:
        return dict(self._active)

    def load_from_directory(self, directory: Path) -> int:
        """Load all skills from a directory. Returns count of skills loaded."""
        if not directory.is_dir():
            return 0

        count = 0
        for path in sorted(directory.iterdir()):
            skill = None
            if path.suffix == ".toml":
                skill = self._load_toml_skill(path)
            elif path.suffix == ".md":
                skill = self._load_markdown_skill(path)

            if skill:
                self._available[skill.name] = skill
                count += 1

        return count

    def load_builtin_skills(self) -> int:
        """Load built-in skills shipped with PuterUI."""
        if BUILTIN_SKILLS_DIR.is_dir():
            return self.load_from_directory(BUILTIN_SKILLS_DIR)
        return 0

    def load_project_skills(self, project_dir: Path) -> int:
        """Load project-level skills from .puterui/skills/."""
        skills_dir = project_dir / ".puterui" / SKILLS_DIR_NAME
        return self.load_from_directory(skills_dir)

    def load_user_skills(self) -> int:
        """Load user-level skills from ~/.config/puterui/skills/."""
        skills_dir = Path.home() / ".config" / "puterui" / SKILLS_DIR_NAME
        return self.load_from_directory(skills_dir)

    def register(self, skill: Skill) -> None:
        """Register a skill in the available pool."""
        self._available[skill.name] = skill

    def activate(self, name: str) -> bool:
        """Activate a skill by name."""
        if name in self._available:
            self._active[name] = self._available[name]
            return True
        return False

    def deactivate(self, name: str) -> bool:
        """Deactivate a skill."""
        if name in self._active:
            del self._active[name]
            return True
        return False

    def get_active_prompt(self) -> str:
        """Get combined prompt text from all active skills."""
        if not self._active:
            return ""
        parts = ["\n# Active Skills\n"]
        for skill in self._active.values():
            parts.append(skill.to_prompt_section())
        return "\n".join(parts)

    def _load_toml_skill(self, path: Path) -> Optional[Skill]:
        """Load a skill from a TOML file."""
        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
        except Exception:
            return None

        name = data.get("name", path.stem)
        return Skill(
            name=name,
            description=data.get("description", ""),
            instructions=data.get("instructions", ""),
            tags=list(data.get("tags", [])),
            source_path=str(path),
        )

    def _load_markdown_skill(self, path: Path) -> Optional[Skill]:
        """Load a skill from a Markdown file.

        The first line starting with # is the name.
        Everything else is instructions.
        """
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            return None

        lines = text.strip().splitlines()
        name = path.stem
        description = ""
        instructions_lines = []

        for i, line in enumerate(lines):
            if line.startswith("# ") and i == 0:
                name = line[2:].strip()
            elif line.startswith("> ") and not description:
                description = line[2:].strip()
            else:
                instructions_lines.append(line)

        return Skill(
            name=name,
            description=description,
            instructions="\n".join(instructions_lines).strip(),
            source_path=str(path),
        )
