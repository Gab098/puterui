"""Tool definitions and implementations for the PuterUI agent."""

from __future__ import annotations

import asyncio
import ipaddress
import os
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
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
            "name": "fetch_url",
            "description": (
                "Fetch a URL over HTTP(S) and return response metadata and body preview. "
                "Useful for recon, API inspection, and debugging web flows."
            ),
            "parameters": {
                "type": "object",
                "required": ["url"],
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to fetch.",
                    },
                    "method": {
                        "type": "string",
                        "description": "HTTP method (default GET).",
                    },
                    "data": {
                        "type": "string",
                        "description": "Optional request body to send.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": (
                "Search the web for a query and return top result links. "
                "Useful for finding alternative tools, docs, and exploitation references."
            ),
            "parameters": {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query text.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default 5).",
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
    {
        "type": "function",
        "function": {
            "name": "terminal_exec",
            "description": (
                "Execute a command in a persistent terminal session. "
                "The session preserves working directory between commands. "
                "No command restrictions -- full terminal access."
            ),
            "parameters": {
                "type": "object",
                "required": ["command"],
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute.",
                    },
                    "session": {
                        "type": "string",
                        "description": (
                            "Terminal session name (default: 'default'). "
                            "Use different names for parallel workflows."
                        ),
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_navigate",
            "description": "Open a URL in the controlled browser.",
            "parameters": {
                "type": "object",
                "required": ["url"],
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to navigate to.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_get_text",
            "description": (
                "Get the visible text content of the current browser page."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_click",
            "description": "Click an element on the page by CSS selector.",
            "parameters": {
                "type": "object",
                "required": ["selector"],
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS selector for the element to click.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_type",
            "description": "Type text into an input element on the page.",
            "parameters": {
                "type": "object",
                "required": ["selector", "text"],
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS selector for the input element.",
                    },
                    "text": {
                        "type": "string",
                        "description": "Text to type into the element.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_screenshot",
            "description": "Take a screenshot of the current browser page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to save the screenshot (optional).",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_js",
            "description": "Execute JavaScript in the browser and return result.",
            "parameters": {
                "type": "object",
                "required": ["script"],
                "properties": {
                    "script": {
                        "type": "string",
                        "description": "JavaScript code to execute.",
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




def _validate_network_url(url: str) -> str | None:
    """Return an error message if URL target is unsafe, else None."""
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return "Error: invalid URL."

    if parsed.scheme not in {"http", "https"}:
        return "Error: only http:// and https:// URLs are allowed."

    host = parsed.hostname
    if not host:
        return "Error: URL must include a hostname."

    if host.lower() in {"localhost"}:
        return "Error: localhost targets are blocked for safety."

    def _is_blocked_ip(ip_str: str) -> bool:
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            return False
        return (
            ip_obj.is_loopback
            or ip_obj.is_private
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
        )

    if _is_blocked_ip(host):
        return "Error: private or local network targets are blocked for safety."

    try:
        _, _, ips = socket.gethostbyname_ex(host)
    except socket.gaierror:
        return None

    for ip_str in ips:
        if _is_blocked_ip(ip_str):
            return "Error: resolved target points to a blocked local/private address."

    return None

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


def _to_display_path(path: Path) -> str:
    """Normalize path separators for stable cross-platform display."""
    return path.as_posix()


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

    if not old:
        return "Error: old_string cannot be empty."

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
                entries.append(f"{_to_display_path(rel)}{suffix}")
        else:
            for item in sorted(path.iterdir()):
                if item.name.startswith("."):
                    continue
                rel = item.relative_to(project_dir)
                suffix = "/" if item.is_dir() else ""
                entries.append(f"{_to_display_path(rel)}{suffix}")

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
                    matches.append(f"{_to_display_path(rel)}:{i}: {line.strip()}")
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


async def tool_fetch_url(args: dict[str, Any]) -> str:
    """Fetch a URL using urllib and return response details."""
    url = args.get("url", "").strip()
    if not url:
        return "Error: no URL provided."

    if safety_error := _validate_network_url(url):
        return safety_error

    method = str(args.get("method", "GET")).upper()
    data_str = args.get("data")
    data = data_str.encode("utf-8") if isinstance(data_str, str) else None

    request = urllib.request.Request(url=url, method=method, data=data)
    request.add_header("User-Agent", "puterui-fetch-url/1.0")

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw_body = response.read(12000)
            body = raw_body.decode("utf-8", errors="replace")
            headers = "\n".join(f"{k}: {v}" for k, v in response.headers.items())
            return (
                f"URL: {url}\n"
                f"Status: {response.status}\n"
                f"Final URL: {response.geturl()}\n"
                f"Headers:\n{headers}\n\n"
                f"Body preview (max 12KB):\n{body}"
            )
    except urllib.error.HTTPError as exc:
        body = exc.read(6000).decode("utf-8", errors="replace")
        return f"HTTP error {exc.code}: {exc.reason}\nURL: {url}\nBody:\n{body}"
    except urllib.error.URLError as exc:
        return f"Network error: {exc.reason}"
    except Exception as exc:
        return f"Error fetching URL: {exc}"


async def tool_search_web(args: dict[str, Any]) -> str:
    """Search the web via DuckDuckGo HTML and return top links."""
    query = args.get("query", "").strip()
    if not query:
        return "Error: no query provided."

    try:
        max_results = int(args.get("max_results", 5))
    except (TypeError, ValueError):
        return "Error: max_results must be an integer."
    max_results = min(max(max_results, 1), 10)

    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://duckduckgo.com/html/?q={encoded_query}"
    request = urllib.request.Request(url=url, method="GET")
    request.add_header("User-Agent", "puterui-search-web/1.0")

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            html = response.read(80000).decode("utf-8", errors="replace")

        matches = re.findall(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not matches:
            return f"No results found for query: {query}"

        lines = [f"Search query: {query}"]
        for idx, (href, title_html) in enumerate(matches[:max_results], start=1):
            title = re.sub(r"<[^>]+>", "", title_html).strip()
            lines.append(f"{idx}. {title}\n   {href}")

        lines.append("\nTip: use fetch_url on a result link for deeper inspection.")
        return "\n".join(lines)
    except urllib.error.URLError as exc:
        return f"Network error: {exc.reason}"
    except Exception as exc:
        return f"Error searching web: {exc}"


# ---------------------------------------------------------------------------
# Terminal tool handlers
# ---------------------------------------------------------------------------

async def tool_terminal_exec(
    args: dict[str, Any],
    project_dir: Path,
    terminal_manager: Any = None,
) -> str:
    """Execute a command in a persistent terminal session."""
    if terminal_manager is None:
        return "Error: terminal manager not available."

    session_name = args.get("session", "default")
    command = args.get("command", "")
    if not command:
        return "Error: no command provided."

    session = terminal_manager.get_session(session_name)
    if session is None:
        session = terminal_manager.create_session(name=session_name)

    result = await session.execute(command)

    output_parts = []
    if result.stdout:
        stdout = result.stdout
        if len(stdout) > 10000:
            stdout = stdout[:10000] + "\n... (truncated)"
        output_parts.append(stdout)
    if result.stderr:
        stderr = result.stderr
        if len(stderr) > 5000:
            stderr = stderr[:5000] + "\n... (truncated)"
        output_parts.append(f"[stderr]\n{stderr}")

    output = "\n".join(output_parts) if output_parts else "(no output)"
    return f"{output}\n[exit code: {result.exit_code}] [cwd: {result.cwd}]"


# ---------------------------------------------------------------------------
# Browser tool handlers
# ---------------------------------------------------------------------------

async def tool_browser_navigate(
    args: dict[str, Any], browser: Any = None
) -> str:
    """Navigate to a URL in the browser."""
    if browser is None:
        return "Error: browser not available. Use /browser start first."

    start_error = await _ensure_browser_started(browser)
    if start_error:
        return start_error

    url = args.get("url", "")
    if not url:
        return "Error: no URL provided."

    result = await browser.navigate(url)
    if result.success:
        return result.data
    return f"Error: {result.error}"


async def tool_browser_get_text(
    args: dict[str, Any], browser: Any = None
) -> str:
    """Get page text from the browser."""
    if browser is None:
        return "Error: browser not available."

    start_error = await _ensure_browser_started(browser)
    if start_error:
        return start_error

    result = await browser.get_text()
    if result.success:
        header = f"Page: {result.title} ({result.url})\n---\n"
        return header + result.data
    return f"Error: {result.error}"


async def tool_browser_click(
    args: dict[str, Any], browser: Any = None
) -> str:
    """Click an element in the browser."""
    if browser is None:
        return "Error: browser not available."

    start_error = await _ensure_browser_started(browser)
    if start_error:
        return start_error

    selector = args.get("selector", "")
    if not selector:
        return "Error: no selector provided."

    result = await browser.click(selector)
    if result.success:
        return result.data
    return f"Error: {result.error}"


async def tool_browser_type(
    args: dict[str, Any], browser: Any = None
) -> str:
    """Type text into a browser element."""
    if browser is None:
        return "Error: browser not available."

    start_error = await _ensure_browser_started(browser)
    if start_error:
        return start_error

    selector = args.get("selector", "")
    text = args.get("text", "")
    if not selector or not text:
        return "Error: selector and text are required."

    result = await browser.type_text(selector, text)
    if result.success:
        return result.data
    return f"Error: {result.error}"


async def tool_browser_screenshot(
    args: dict[str, Any], browser: Any = None
) -> str:
    """Take a browser screenshot."""
    if browser is None:
        return "Error: browser not available."

    start_error = await _ensure_browser_started(browser)
    if start_error:
        return start_error

    path = args.get("path")
    result = await browser.screenshot(path)
    if result.success:
        return result.data
    return f"Error: {result.error}"


async def tool_browser_js(
    args: dict[str, Any], browser: Any = None
) -> str:
    """Execute JavaScript in the browser."""
    if browser is None:
        return "Error: browser not available."

    start_error = await _ensure_browser_started(browser)
    if start_error:
        return start_error

    script = args.get("script", "")
    if not script:
        return "Error: no script provided."

    result = await browser.execute_js(script)
    if result.success:
        return result.data
    return f"Error: {result.error}"


async def _ensure_browser_started(browser: Any) -> str | None:
    """Ensure browser backend is running before browser actions."""
    try:
        status = browser.status()
    except Exception:
        status = "Not running"

    if status != "Not running":
        return None

    start_result = await browser.start()
    if start_result.success:
        return None
    return (
        "Error: browser is not running and auto-start failed. "
        f"{start_result.error}"
    )


# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------

FILE_TOOL_HANDLERS = {
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "edit_file": tool_edit_file,
    "list_files": tool_list_files,
    "search_files": tool_search_files,
    "run_command": tool_run_command,
}

NETWORK_TOOL_HANDLERS = {
    "fetch_url": tool_fetch_url,
    "search_web": tool_search_web,
}

TERMINAL_TOOL_HANDLERS = {
    "terminal_exec": tool_terminal_exec,
}

BROWSER_TOOL_HANDLERS = {
    "browser_navigate": tool_browser_navigate,
    "browser_get_text": tool_browser_get_text,
    "browser_click": tool_browser_click,
    "browser_type": tool_browser_type,
    "browser_screenshot": tool_browser_screenshot,
    "browser_js": tool_browser_js,
}

# Combined for backwards compat
TOOL_HANDLERS = {
    **FILE_TOOL_HANDLERS,
    **NETWORK_TOOL_HANDLERS,
    **TERMINAL_TOOL_HANDLERS,
    **BROWSER_TOOL_HANDLERS,
}


async def execute_tool(
    name: str,
    args: dict[str, Any],
    project_dir: Path,
    allowed_commands: list[str] | None = None,
    terminal_manager: Any = None,
    browser: Any = None,
) -> str:
    """Dispatch and execute a tool call."""
    if name in FILE_TOOL_HANDLERS:
        if name == "run_command":
            return await tool_run_command(args, project_dir, allowed_commands or [])
        return await FILE_TOOL_HANDLERS[name](args, project_dir)

    if name in NETWORK_TOOL_HANDLERS:
        return await NETWORK_TOOL_HANDLERS[name](args)

    if name in TERMINAL_TOOL_HANDLERS:
        return await tool_terminal_exec(args, project_dir, terminal_manager)

    if name in BROWSER_TOOL_HANDLERS:
        return await BROWSER_TOOL_HANDLERS[name](args, browser)

    return f"Error: unknown tool '{name}'."
