"""Tests for the skills system."""

from pathlib import Path

from puterui.skills import Skill, SkillRegistry


def test_skill_to_prompt():
    """Skill should format as a prompt section."""
    skill = Skill(
        name="test-skill",
        description="A test skill",
        instructions="Do the thing.",
    )
    prompt = skill.to_prompt_section()
    assert "test-skill" in prompt
    assert "Do the thing." in prompt


def test_registry_empty():
    """Empty registry should have no skills."""
    registry = SkillRegistry()
    assert len(registry.available) == 0
    assert len(registry.active) == 0
    assert registry.get_active_prompt() == ""


def test_registry_load_toml_skill(tmp_path):
    """Registry should load TOML skills."""
    skill_file = tmp_path / "my-skill.toml"
    skill_file.write_text(
        'name = "my-skill"\n'
        'description = "A cool skill"\n'
        'instructions = "Be cool."\n'
        'tags = ["testing"]\n'
    )
    registry = SkillRegistry()
    count = registry.load_from_directory(tmp_path)
    assert count == 1
    assert "my-skill" in registry.available


def test_registry_load_markdown_skill(tmp_path):
    """Registry should load Markdown skills."""
    skill_file = tmp_path / "md-skill.md"
    skill_file.write_text(
        "# Markdown Skill\n"
        "> A skill from markdown\n"
        "\n"
        "Follow these steps:\n"
        "1. Step one\n"
        "2. Step two\n"
    )
    registry = SkillRegistry()
    count = registry.load_from_directory(tmp_path)
    assert count == 1
    skill = registry.available.get("Markdown Skill")
    assert skill is not None
    assert "A skill from markdown" in skill.description
    assert "Step one" in skill.instructions


def test_registry_activate_deactivate(tmp_path):
    """Activation and deactivation should work."""
    skill_file = tmp_path / "toggle.toml"
    skill_file.write_text(
        'name = "toggle"\n'
        'instructions = "Toggle me."\n'
    )
    registry = SkillRegistry()
    registry.load_from_directory(tmp_path)

    assert registry.activate("toggle") is True
    assert "toggle" in registry.active
    assert "toggle" in registry.get_active_prompt()

    assert registry.deactivate("toggle") is True
    assert "toggle" not in registry.active

    assert registry.activate("nonexistent") is False
    assert registry.deactivate("nonexistent") is False


def test_registry_load_builtin():
    """Builtin skills should load if directory exists."""
    registry = SkillRegistry()
    count = registry.load_builtin_skills()
    # We have 3 builtin skills
    assert count >= 3
    assert "Code Review" in registry.available
    assert "Refactor" in registry.available
    assert "Git Workflow" in registry.available


def test_registry_nonexistent_directory():
    """Loading from a nonexistent directory should return 0."""
    registry = SkillRegistry()
    count = registry.load_from_directory(Path("/nonexistent/dir"))
    assert count == 0
