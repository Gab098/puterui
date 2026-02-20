"""OpenClaw compatibility layer for PuterUI.

Loads OpenClaw-format configuration files (soul.json, identity.yaml, etc.)
and converts them into PuterUI Persona and Skill objects, so users can
drop in their existing OpenClaw configs and they just work.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

from puterui.persona import Persona
from puterui.skills import Skill, SkillRegistry

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def load_openclaw_soul(path: Path) -> Optional[Persona]:
    """Load an OpenClaw soul.json or soul.yaml file as a Persona.

    OpenClaw soul files typically contain:
    - name: str
    - identity/role: str
    - personality/traits: list[str]
    - instructions/rules: list[str]
    - voice/style: str
    """
    if not path.exists():
        return None

    data = _load_data_file(path)
    if data is None:
        return None

    persona = Persona()

    # Map OpenClaw fields to Persona fields
    if "name" in data:
        persona.name = str(data["name"])

    # OpenClaw uses "identity" or "role"
    for key in ("identity", "role", "description"):
        if key in data:
            persona.role = str(data[key])
            break

    # Personality / traits
    for key in ("personality", "traits", "characteristics"):
        if key in data:
            val = data[key]
            if isinstance(val, list):
                persona.traits = [str(t) for t in val]
            elif isinstance(val, str):
                persona.traits = [s.strip() for s in val.split(",")]
            break

    # Communication style / voice
    for key in ("voice", "style", "communication_style", "tone"):
        if key in data:
            persona.communication_style = str(data[key])
            break

    # Values
    for key in ("values", "principles", "guidelines"):
        if key in data:
            val = data[key]
            if isinstance(val, list):
                persona.values = [str(v) for v in val]
            break

    # Rules / instructions
    for key in ("rules", "instructions", "constraints", "boundaries"):
        if key in data:
            val = data[key]
            if isinstance(val, list):
                persona.rules = [str(r) for r in val]
            break

    # Backstory
    for key in ("backstory", "background", "lore", "context"):
        if key in data:
            persona.backstory = str(data[key])
            break

    # Quirks
    for key in ("quirks", "mannerisms", "habits"):
        if key in data:
            val = data[key]
            if isinstance(val, list):
                persona.quirks = [str(q) for q in val]
            break

    return persona


def load_openclaw_skills(directory: Path, registry: SkillRegistry) -> int:
    """Load OpenClaw-format skill files from a directory.

    OpenClaw skills can be JSON, YAML, TOML, or Markdown files with
    fields like: name, description, prompt/instructions, tags.
    """
    if not directory.is_dir():
        return 0

    count = 0
    for path in sorted(directory.iterdir()):
        skill = None
        if path.suffix in (".json", ".yaml", ".yml", ".toml"):
            skill = _load_openclaw_skill_data(path)
        elif path.suffix == ".md":
            # Already handled by the standard skill loader
            pass

        if skill:
            registry._available[skill.name] = skill
            count += 1

    return count


def detect_openclaw_project(project_dir: Path) -> dict[str, Path]:
    """Detect OpenClaw config files in a project directory.

    Returns a dict of detected file types and their paths.
    """
    detected: dict[str, Path] = {}

    # Check for soul/identity files
    soul_names = [
        "soul.json", "soul.yaml", "soul.yml", "soul.toml",
        "identity.json", "identity.yaml", "identity.yml",
        ".openclaw/soul.json", ".openclaw/soul.yaml",
        ".openclaw/identity.json",
    ]
    for name in soul_names:
        p = project_dir / name
        if p.exists():
            detected["soul"] = p
            break

    # Check for skills directory
    skill_dirs = [
        ".openclaw/skills",
        ".openclaw/prompts",
        "skills",
        "prompts",
    ]
    for name in skill_dirs:
        p = project_dir / name
        if p.is_dir():
            detected["skills"] = p
            break

    # Check for config
    config_names = [
        ".openclaw/config.json",
        ".openclaw/config.yaml",
        ".openclaw/config.toml",
        "openclaw.json",
        "openclaw.toml",
    ]
    for name in config_names:
        p = project_dir / name
        if p.exists():
            detected["config"] = p
            break

    return detected


def auto_import_openclaw(
    project_dir: Path,
    persona: Persona,
    skills: SkillRegistry,
) -> bool:
    """Auto-detect and import OpenClaw configs from a project.

    Returns True if any OpenClaw files were found and imported.
    """
    detected = detect_openclaw_project(project_dir)
    imported = False

    if "soul" in detected:
        oc_persona = load_openclaw_soul(detected["soul"])
        if oc_persona:
            # Merge into existing persona
            persona.name = oc_persona.name
            persona.role = oc_persona.role
            if oc_persona.traits:
                persona.traits = oc_persona.traits
            if oc_persona.communication_style:
                persona.communication_style = oc_persona.communication_style
            if oc_persona.values:
                persona.values = oc_persona.values
            if oc_persona.rules:
                persona.rules = oc_persona.rules
            if oc_persona.backstory:
                persona.backstory = oc_persona.backstory
            if oc_persona.quirks:
                persona.quirks = oc_persona.quirks
            imported = True

    if "skills" in detected:
        count = load_openclaw_skills(detected["skills"], skills)
        if count > 0:
            imported = True

    return imported


def _load_data_file(path: Path) -> Optional[dict]:
    """Load a JSON, YAML, or TOML file into a dict."""
    try:
        if path.suffix == ".json":
            return json.loads(path.read_text(encoding="utf-8"))
        elif path.suffix in (".yaml", ".yml"):
            # Try to import yaml, fall back to basic parsing
            try:
                import yaml

                return yaml.safe_load(path.read_text(encoding="utf-8"))
            except ImportError:
                return _basic_yaml_parse(path.read_text(encoding="utf-8"))
        elif path.suffix == ".toml":
            with open(path, "rb") as f:
                return tomllib.load(f)
    except Exception:
        pass
    return None


def _basic_yaml_parse(text: str) -> dict:
    """Very basic YAML-like parser for simple key: value files.

    Only handles flat key-value pairs and simple lists.
    For full YAML support, install PyYAML.
    """
    result: dict = {}
    current_key = None
    current_list: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("- ") and current_key:
            current_list.append(stripped[2:].strip().strip("\"'"))
        elif ":" in stripped:
            if current_key and current_list:
                result[current_key] = current_list
                current_list = []

            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip().strip("\"'")
            current_key = key
            if value:
                result[key] = value
                current_key = key
        else:
            if current_key and not current_list:
                result[current_key] = (
                    result.get(current_key, "") + " " + stripped
                ).strip()

    if current_key and current_list:
        result[current_key] = current_list

    return result


def _load_openclaw_skill_data(path: Path) -> Optional[Skill]:
    """Load a single OpenClaw skill from a data file."""
    data = _load_data_file(path)
    if data is None:
        return None

    name = data.get("name", path.stem)
    description = ""
    instructions = ""
    tags: list[str] = []

    for key in ("description", "desc", "summary"):
        if key in data:
            description = str(data[key])
            break

    for key in ("instructions", "prompt", "content", "system_prompt"):
        if key in data:
            instructions = str(data[key])
            break

    for key in ("tags", "categories", "labels"):
        if key in data:
            val = data[key]
            if isinstance(val, list):
                tags = [str(t) for t in val]
            break

    return Skill(
        name=name,
        description=description,
        instructions=instructions,
        tags=tags,
        source_path=str(path),
    )
