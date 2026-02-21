"""Tests for the persona/soul system."""

from pathlib import Path

from puterui.persona import Persona


def test_default_persona():
    """Default persona should have sensible values."""
    persona = Persona()
    assert persona.name == "Puter"
    assert persona.role == "AI coding assistant"
    assert len(persona.traits) > 0
    assert len(persona.values) > 0
    assert len(persona.rules) > 0


def test_persona_to_system_prompt():
    """System prompt should include name and role."""
    persona = Persona(name="TestBot", role="test helper")
    prompt = persona.to_system_prompt()
    assert "TestBot" in prompt
    assert "test helper" in prompt


def test_persona_with_backstory():
    """Backstory should appear in system prompt."""
    persona = Persona(
        name="CodeWiz",
        backstory="A wizard who codes in assembly for fun.",
    )
    prompt = persona.to_system_prompt()
    assert "wizard" in prompt
    assert "assembly" in prompt


def test_persona_with_quirks():
    """Quirks should appear in system prompt."""
    persona = Persona(quirks=["loves semicolons", "hates tabs"])
    prompt = persona.to_system_prompt()
    assert "loves semicolons" in prompt
    assert "hates tabs" in prompt


def test_persona_summary():
    """Summary should include name and role."""
    persona = Persona(name="Bot", role="helper")
    summary = persona.summary()
    assert "Bot" in summary
    assert "helper" in summary


def test_persona_load_from_file(tmp_path):
    """Persona should load from a TOML file."""
    persona_file = tmp_path / "persona.toml"
    persona_file.write_text(
        'name = "CustomBot"\n'
        'role = "custom assistant"\n'
        'backstory = "Born in a TOML file"\n'
        'traits = ["witty", "sharp"]\n'
    )
    persona = Persona.load(project_dir=tmp_path)
    assert persona.name == "CustomBot"
    assert persona.role == "custom assistant"
    assert persona.backstory == "Born in a TOML file"
    assert persona.traits == ["witty", "sharp"]


def test_persona_load_defaults_no_file():
    """Persona should use defaults when no file exists."""
    persona = Persona.load(project_dir=Path("/nonexistent"))
    assert persona.name == "Puter"
