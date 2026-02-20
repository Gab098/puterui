"""Tests for the terminal session manager."""

import pytest

from puterui.terminal import TerminalManager, TerminalSession


@pytest.fixture
def manager(tmp_path):
    return TerminalManager(str(tmp_path))


def test_create_session(manager):
    """Creating a session should work."""
    session = manager.create_session(name="test")
    assert session.session_id == "test"
    assert "test" in manager.list_sessions()


def test_get_or_create_default(manager):
    """Default session should be created lazily."""
    session = manager.get_or_create_default()
    assert session.session_id == "default"
    assert "default" in manager.list_sessions()

    # Second call should return the same session
    session2 = manager.get_or_create_default()
    assert session2 is session


def test_get_session(manager):
    """Getting a session by name should work."""
    manager.create_session(name="s1")
    assert manager.get_session("s1") is not None
    assert manager.get_session("nonexistent") is None


def test_list_sessions(manager):
    """Listing sessions should return all names."""
    manager.create_session(name="a")
    manager.create_session(name="b")
    sessions = manager.list_sessions()
    assert "a" in sessions
    assert "b" in sessions


@pytest.mark.asyncio
async def test_execute_command(tmp_path):
    """Session should execute commands and return results."""
    session = TerminalSession(session_id="test", cwd=str(tmp_path))
    result = await session.execute("echo hello")
    assert "hello" in result.stdout
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_execute_preserves_cwd(tmp_path):
    """Session should track working directory changes."""
    subdir = tmp_path / "subdir"
    subdir.mkdir()

    session = TerminalSession(session_id="test", cwd=str(tmp_path))
    result = await session.execute(f"cd {subdir}")
    assert result.cwd == str(subdir)


@pytest.mark.asyncio
async def test_execute_timeout(tmp_path):
    """Commands that exceed timeout should fail gracefully."""
    session = TerminalSession(session_id="test", cwd=str(tmp_path))
    result = await session.execute("sleep 10", timeout=0.5)
    assert result.exit_code == -1
    assert "timed out" in result.stderr


@pytest.mark.asyncio
async def test_close_session(manager):
    """Closing a session should remove it."""
    manager.create_session(name="closeme")
    closed = await manager.close_session("closeme")
    assert closed is True
    assert "closeme" not in manager.list_sessions()

    # Closing again should return False
    closed = await manager.close_session("closeme")
    assert closed is False


@pytest.mark.asyncio
async def test_command_history(tmp_path):
    """Session should track command history."""
    session = TerminalSession(session_id="test", cwd=str(tmp_path))
    await session.execute("echo one")
    await session.execute("echo two")
    assert len(session.history) == 2
    assert session.history[0].command == "echo one"
    assert session.history[1].command == "echo two"
