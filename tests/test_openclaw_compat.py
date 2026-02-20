"""Tests for OpenClaw compatibility layer."""

import json
from pathlib import Path

from puterui.openclaw_compat import (
    auto_import_openclaw,
    detect_openclaw_project,
    load_openclaw_soul,
)
from puterui.persona import Persona
from puterui.skills import SkillRegistry


def test_load_soul_json(tmp_path):
    """Should load an OpenClaw soul.json file."""
    soul = {
        "name": "TestClaw",
        "identity": "security researcher",
        "personality": ["thorough", "cautious"],
        "voice": "professional",
        "values": ["accuracy", "ethics"],
        "rules": ["always verify scope"],
        "backstory": "A veteran researcher.",
        "quirks": ["loves CVSS scores"],
    }
    soul_path = tmp_path / "soul.json"
    soul_path.write_text(json.dumps(soul))

    persona = load_openclaw_soul(soul_path)
    assert persona is not None
    assert persona.name == "TestClaw"
    assert persona.role == "security researcher"
    assert persona.traits == ["thorough", "cautious"]
    assert persona.communication_style == "professional"
    assert persona.backstory == "A veteran researcher."
    assert "loves CVSS scores" in persona.quirks


def test_load_soul_nonexistent():
    """Should return None for missing file."""
    result = load_openclaw_soul(Path("/nonexistent/soul.json"))
    assert result is None


def test_detect_openclaw_project(tmp_path):
    """Should detect OpenClaw files in a project."""
    # Create soul.json
    (tmp_path / "soul.json").write_text('{"name": "test"}')

    # Create skills dir
    skills_dir = tmp_path / ".openclaw" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "recon.json").write_text(
        '{"name": "recon", "instructions": "do recon"}'
    )

    detected = detect_openclaw_project(tmp_path)
    assert "soul" in detected
    assert "skills" in detected


def test_detect_openclaw_empty(tmp_path):
    """Should return empty dict for non-OpenClaw project."""
    detected = detect_openclaw_project(tmp_path)
    assert len(detected) == 0


def test_auto_import_openclaw(tmp_path):
    """Should import OpenClaw soul and skills."""
    (tmp_path / "soul.json").write_text(
        json.dumps({
            "name": "ClawBot",
            "identity": "pentest assistant",
            "personality": ["aggressive", "thorough"],
        })
    )

    skills_dir = tmp_path / ".openclaw" / "skills"
    skills_dir.mkdir(parents=True)
    (skills_dir / "scan.json").write_text(
        json.dumps({
            "name": "Network Scan",
            "description": "Network scanning skill",
            "instructions": "Use nmap.",
        })
    )

    persona = Persona()
    skills = SkillRegistry()

    result = auto_import_openclaw(tmp_path, persona, skills)
    assert result is True
    assert persona.name == "ClawBot"
    assert persona.role == "pentest assistant"
    assert "Network Scan" in skills.available


def test_auto_import_no_openclaw(tmp_path):
    """Should return False when no OpenClaw files found."""
    persona = Persona()
    skills = SkillRegistry()
    result = auto_import_openclaw(tmp_path, persona, skills)
    assert result is False


def test_builtin_personas():
    """Builtin personas should be loadable."""
    builtins = Persona.list_builtins()
    assert "hacker" in builtins
    assert "osint-analyst" in builtins

    hacker = Persona.load_builtin("hacker")
    assert hacker is not None
    assert hacker.name == "Ghost"
    assert "offensive security" in hacker.role

    osint = Persona.load_builtin("osint-analyst")
    assert osint is not None
    assert osint.name == "Recon"
