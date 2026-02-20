"""Tests for tool implementations."""

from pathlib import Path

import pytest

from puterui.tools import (
    execute_tool,
    tool_edit_file,
    tool_list_files,
    tool_read_file,
    tool_run_command,
    tool_search_files,
    tool_write_file,
)


@pytest.fixture
def project(tmp_path):
    """Create a temporary project directory with some files."""
    (tmp_path / "hello.py").write_text("print('hello world')\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text(
        "def main():\n    print('main')\n\nif __name__ == '__main__':\n    main()\n"
    )
    (tmp_path / "README.md").write_text("# Test Project\n\nA test project.\n")
    return tmp_path


@pytest.mark.asyncio
async def test_read_file(project):
    result = await tool_read_file({"path": "hello.py"}, project)
    assert "hello world" in result
    assert "hello.py" in result


@pytest.mark.asyncio
async def test_read_file_not_found(project):
    result = await tool_read_file({"path": "nonexistent.py"}, project)
    assert "Error" in result
    assert "does not exist" in result


@pytest.mark.asyncio
async def test_read_file_outside_project(project):
    result = await tool_read_file({"path": "/etc/passwd"}, project)
    assert "Error" in result
    assert "outside" in result


@pytest.mark.asyncio
async def test_read_file_with_offset_limit(project):
    result = await tool_read_file(
        {"path": "src/main.py", "offset": 2, "limit": 2}, project
    )
    assert "print('main')" in result
    assert "showing lines" in result


@pytest.mark.asyncio
async def test_write_file(project):
    result = await tool_write_file(
        {"path": "new_file.txt", "content": "hello from test"}, project
    )
    assert "Successfully wrote" in result
    assert (project / "new_file.txt").read_text() == "hello from test"


@pytest.mark.asyncio
async def test_write_file_creates_dirs(project):
    result = await tool_write_file(
        {"path": "deep/nested/dir/file.txt", "content": "nested"}, project
    )
    assert "Successfully wrote" in result
    assert (project / "deep" / "nested" / "dir" / "file.txt").read_text() == "nested"


@pytest.mark.asyncio
async def test_edit_file(project):
    result = await tool_edit_file(
        {
            "path": "hello.py",
            "old_string": "print('hello world')",
            "new_string": "print('goodbye world')",
        },
        project,
    )
    assert "Successfully edited" in result
    assert "goodbye world" in (project / "hello.py").read_text()


@pytest.mark.asyncio
async def test_edit_file_not_found_string(project):
    result = await tool_edit_file(
        {
            "path": "hello.py",
            "old_string": "this does not exist",
            "new_string": "replacement",
        },
        project,
    )
    assert "Error" in result
    assert "not found" in result


@pytest.mark.asyncio
async def test_list_files(project):
    result = await tool_list_files({"path": "."}, project)
    assert "hello.py" in result
    assert "README.md" in result
    assert "src/" in result


@pytest.mark.asyncio
async def test_list_files_recursive(project):
    result = await tool_list_files({"path": ".", "recursive": True}, project)
    assert "src/main.py" in result


@pytest.mark.asyncio
async def test_search_files(project):
    result = await tool_search_files(
        {"path": ".", "pattern": "def main"}, project
    )
    assert "src/main.py" in result
    assert "def main" in result


@pytest.mark.asyncio
async def test_search_files_no_match(project):
    result = await tool_search_files(
        {"path": ".", "pattern": "zzz_nonexistent_zzz"}, project
    )
    assert "No matches" in result


@pytest.mark.asyncio
async def test_search_files_with_glob(project):
    result = await tool_search_files(
        {"path": ".", "pattern": "print", "file_glob": "*.py"}, project
    )
    assert "hello.py" in result


@pytest.mark.asyncio
async def test_run_command(project):
    result = await tool_run_command(
        {"command": "echo hello"}, project, ["echo"]
    )
    assert "hello" in result
    assert "exit code: 0" in result


@pytest.mark.asyncio
async def test_run_command_blocked(project):
    result = await tool_run_command(
        {"command": "rm -rf /"}, project, ["echo", "ls"]
    )
    assert "Error" in result
    assert "not in the allowed list" in result


@pytest.mark.asyncio
async def test_execute_tool_dispatch(project):
    result = await execute_tool(
        "read_file", {"path": "hello.py"}, project
    )
    assert "hello world" in result


@pytest.mark.asyncio
async def test_execute_tool_unknown():
    result = await execute_tool(
        "nonexistent_tool", {}, Path("/tmp")
    )
    assert "unknown tool" in result
