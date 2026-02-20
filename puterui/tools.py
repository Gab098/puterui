"""Tool definitions and implementations for the PuterUI agent."""

from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Ollama tool-call schema definitions
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read the contents of a file at the given path. "
                "Returns the file text or an error message."
            ),
            "parameters": {
                "type": "object",
                "required": ["path"],
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative or absolute path to the file to read.",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "1-based line number to start reading from (default 1).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of lines to return (default 200).",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Write content to a file, creating directories as needed. "
                "Overwrites existing content."
            ),
            "parameters": {
                "type": "object",
                "required": ["path", "content"],
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative or absolute path to write to.",
                    },
                    "content": {
                        "type": "string",
                        "description": "The full content to write to the file.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "Replace an exact string in a file with new content. "
                "The old_string must match exactly (including whitespace)."
            ),
            "parameters": {
                "type": "object",
                "required": ["path", "old_string", "new_string"],
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to edit.",
                    },
                    "old_string": {
                        "type": "string",
                        "description": "The exact text to find and replace.",
                    },
                    "new_string": {
                        "type": "string",
                        "description": "The replacement text.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path.",
            "parameters": {
                "type": "object",
                "required": ["path"],
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list.",
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Whether to list recursively (default false).",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search for a regex pattern across files in a directory.",
            "parameters": {
                "type": "object",
                "required": ["path", "pattern"],
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory to search in.",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to search for.",
                    },
                    "file_glob": {
                        "type": "string",
                        "description": "Optional glob to filter files (e.g. '*.py').",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": (
                "Execute a shell command and return its output. "
                "Only allowed commands can be executed for safety."
            ),
            "parameters": {
                "type": "object",
                "required": ["command"],
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute.",
                    },
                },
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

class ToolError(Exception):
    """Raised when a tool execution fails."""


def _resolve_path(path_str: str, project_dir: Path) -> Path:
    """Resolve a path relative to the project directory."""
    p = Path(path_str)
    if not p.is_absolute():
        p = project_dir / p
    return p.resolve()


def _is_safe_path(path: Path, project_dir: Path) -> bool:
    """Check that a path is within the project directory."""
    try:
        path.resolve().relative_to(project_dir.resolve())
        return True
    except ValueError:
        return False


async def tool_read_file(
    args: dict[str, Any], project_dir: Path
) -> str:
    """Read a file and return its contents with line numbers."""
    path = _resolve_path(args["path"], project_dir)
    if not _is_safe_path(path, project_dir):
        return f"Error: path '{args['path']}' is outside the project directory."
    if not path.exists():
        return f"Error: file '{args['path']}' does not exist."
    if not path.is_file():
        return f"Error: '{args['path']}' is not a file."

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return f"Error reading file: {exc}"

    lines = text.splitlines()
    offset = max(args.get("offset", 1), 1) - 1
    limit = args.get("limit", 200)
    selected = lines[offset : offset + limit]

    numbered = []
    for i, line in enumerate(selected, start=offset + 1):
        numbered.append(f"{i:>5} | {line}")

    total = len(lines)
    header = f"File: {args['path']} ({total} lines)"
    if offset > 0 or offset + limit < total:
        header += f" [showing lines {offset + 1}-{min(offset + limit, total)}]"

    return header + "\n" + "\n".join(numbered)


async def tool_write_file(
    args: dict[str, Any], project_dir: Path
) -> str:
    """Write content to a file."""
    path = _resolve_path(args["path"], project_dir)
    if not _is_safe_path(path, project_dir):
        return f"Error: path '{args['path']}' is outside the project directory."

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(args["content"], encoding="utf-8")
        return f"Successfully wrote {len(args['content'])} bytes to {args['path']}"
    except Exception as exc:
        return f"Error writing file: {exc}"


async def tool_edit_file(
    args: dict[str, Any], project_dir: Path
) -> str:
    """Replace exact text in a file."""
    path = _resolve_path(args["path"], project_dir)
    if not _is_safe_path(path, project_dir):
        return f"Error: path '{args['path']}' is outside the project directory."
    if not path.exists():
        return f"Error: file '{args['path']}' does not exist."

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as exc:
        return f"Error reading file: {exc}"

    old = args["old_string"]
    new = args["new_string"]

    count = content.count(old)
    if count == 0:
        return "Error: old_string not found in file."
    if count > 1:
        return f"Error: old_string found {count} times. Provide more context to make it unique."

    updated = content.replace(old, new, 1)
    try:
        path.write_text(updated, encoding="utf-8")
        return f"Successfully edited {args['path']}"
    except Exception as exc:
        return f"Error writing file: {exc}"


async def tool_list_files(
    args: dict[str, Any], project_dir: Path
) -> str:
    """List files in a directory."""
    path = _resolve_path(args["path"], project_dir)
    if not _is_safe_path(path, project_dir):
        return f"Error: path '{args['path']}' is outside the project directory."
    if not path.exists():
        return f"Error: directory '{args['path']}' does not exist."
    if not path.is_dir():
        return f"Error: '{args['path']}' is not a directory."

    recursive = args.get("recursive", False)
    entries: list[str] = []

    try:
        if recursive:
            for item in sorted(path.rglob("*")):
                if any(part.startswith(".") for part in item.relative_to(path).parts):
                    continue
                rel = item.relative_to(project_dir)
                suffix = "/" if item.is_dir() else ""
                entries.append(f"{rel}{suffix}")
        else:
            for item in sorted(path.iterdir()):
                if item.name.startswith("."):
                    continue
                rel = item.relative_to(project_dir)
                suffix = "/" if item.is_dir() else ""
                entries.append(f"{rel}{suffix}")

        if not entries:
            return f"Directory '{args['path']}' is empty."
        return "\n".join(entries[:500])
    except Exception as exc:
        return f"Error listing files: {exc}"


async def tool_search_files(
    args: dict[str, Any], project_dir: Path
) -> str:
    """Search for a pattern across files."""
    path = _resolve_path(args["path"], project_dir)
    if not _is_safe_path(path, project_dir):
        return f"Error: path '{args['path']}' is outside the project directory."

    pattern_str = args["pattern"]
    try:
        pattern = re.compile(pattern_str, re.IGNORECASE)
    except re.error as exc:
        return f"Error: invalid regex pattern: {exc}"

    file_glob = args.get("file_glob", "*")
    matches: list[str] = []
    max_matches = 100

    try:
        for filepath in sorted(path.rglob(file_glob)):
            if not filepath.is_file():
                continue
            if any(part.startswith(".") for part in filepath.relative_to(path).parts):
                continue
            try:
                text = filepath.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            for i, line in enumerate(text.splitlines(), 1):
                if pattern.search(line):
                    rel = filepath.relative_to(project_dir)
                    matches.append(f"{rel}:{i}: {line.strip()}")
                    if len(matches) >= max_matches:
                        break
            if len(matches) >= max_matches:
                break
    except Exception as exc:
        return f"Error searching: {exc}"

    if not matches:
        return f"No matches found for pattern '{pattern_str}'."

    result = f"Found {len(matches)} match(es):\n" + "\n".join(matches)
    if len(matches) >= max_matches:
        result += "\n... (truncated)"
    return result


async def tool_run_command(
    args: dict[str, Any], project_dir: Path, allowed_commands: list[str]
) -> str:
    """Execute a shell command."""
    command = args["command"].strip()

    # Extract the base command for safety check
    base_cmd = command.split()[0] if command else ""
    # Also handle paths like /usr/bin/git
    base_cmd = os.path.basename(base_cmd)

    if base_cmd not in allowed_commands:
        return (
            f"Error: command '{base_cmd}' is not in the allowed list. "
            f"Allowed: {', '.join(sorted(allowed_commands))}"
        )

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(project_dir),
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
    except asyncio.TimeoutError:
        return "Error: command timed out after 30 seconds."
    except Exception as exc:
        return f"Error running command: {exc}"

    output_parts = []
    if stdout:
        decoded = stdout.decode("utf-8", errors="replace")
        # Truncate large outputs
        if len(decoded) > 10000:
            decoded = decoded[:10000] + "\n... (truncated)"
        output_parts.append(decoded)
    if stderr:
        decoded = stderr.decode("utf-8", errors="replace")
        if len(decoded) > 5000:
            decoded = decoded[:5000] + "\n... (truncated)"
        output_parts.append(f"[stderr]\n{decoded}")

    exit_info = f"[exit code: {proc.returncode}]"
    result = "\n".join(output_parts) if output_parts else "(no output)"
    return f"{result}\n{exit_info}"


# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------

TOOL_HANDLERS = {
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "edit_file": tool_edit_file,
    "list_files": tool_list_files,
    "search_files": tool_search_files,
    "run_command": tool_run_command,
}


async def execute_tool(
    name: str,
    args: dict[str, Any],
    project_dir: Path,
    allowed_commands: list[str] | None = None,
) -> str:
    """Dispatch and execute a tool call."""
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        return f"Error: unknown tool '{name}'."

    if name == "run_command":
        return await handler(args, project_dir, allowed_commands or [])
    return await handler(args, project_dir)
