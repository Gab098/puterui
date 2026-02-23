"""Enhanced terminal control for PuterUI.

Provides persistent shell sessions that the assistant can use to run
sequences of commands with shared state (environment variables, working
directory, etc.) -- like having a real terminal open.
"""

from __future__ import annotations

import asyncio
import os
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class CommandResult:
    """Result of a command execution."""

    stdout: str
    stderr: str
    exit_code: int
    command: str
    cwd: str


@dataclass
class TerminalSession:
    """A persistent shell session with its own state."""

    session_id: str
    cwd: str
    env: dict[str, str] = field(default_factory=dict)
    history: list[CommandResult] = field(default_factory=list)
    _active_proc: Optional[asyncio.subprocess.Process] = field(
        default=None, repr=False
    )
    _max_history: int = 50

    async def execute(self, command: str, timeout: float = 30.0) -> CommandResult:
        """Execute a command in this session.

        Uses a fresh subprocess for each command but preserves the
        working directory via cd tracking.
        """
        sentinel = f"__PUTERUI_END_{id(self)}__"

        if os.name == "nt":
            quoted_cwd = self.cwd.replace('"', '""')
            wrapped = (
                f'cd /d "{quoted_cwd}" && '
                f"{command} & "
                "set __exit_code=%errorlevel% & "
                f"echo {sentinel} & "
                "cd & "
                "exit /b %__exit_code%"
            )
            spawn = asyncio.create_subprocess_exec
            spawn_args = ["cmd.exe", "/d", "/s", "/c", wrapped]
        else:
            quoted_cwd = shlex.quote(self.cwd)
            wrapped = (
                f"cd {quoted_cwd} 2>/dev/null; "
                f"{command}; "
                f"__exit_code=$?; "
                f'echo "{sentinel}"; '
                "pwd; "
                "exit $__exit_code"
            )
            spawn = asyncio.create_subprocess_shell
            spawn_args = [wrapped]

        proc: Optional[asyncio.subprocess.Process] = None
        try:
            proc = await spawn(
                *spawn_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cwd,
                env={**os.environ, **self.env},
            )
            self._active_proc = proc
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            self._active_proc = None
        except asyncio.TimeoutError:
            # Kill the timed-out process
            if proc and proc.returncode is None:
                try:
                    proc.kill()
                    await proc.wait()
                except Exception:
                    pass
            self._active_proc = None
            return CommandResult(
                stdout="",
                stderr="Error: command timed out",
                exit_code=-1,
                command=command,
                cwd=self.cwd,
            )
        except Exception as exc:
            return CommandResult(
                stdout="",
                stderr=f"Error: {exc}",
                exit_code=-1,
                command=command,
                cwd=self.cwd,
            )

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")

        # Extract new cwd from output
        if sentinel in stdout:
            parts = stdout.split(sentinel, 1)
            stdout = parts[0]
            new_cwd = parts[1].strip().splitlines()
            if new_cwd:
                candidate = new_cwd[0].strip()
                if candidate and Path(candidate).is_dir():
                    self.cwd = candidate

        exit_code = proc.returncode if proc and proc.returncode is not None else -1

        result = CommandResult(
            stdout=stdout.rstrip(),
            stderr=stderr.rstrip(),
            exit_code=exit_code,
            command=command,
            cwd=self.cwd,
        )

        self.history.append(result)
        if len(self.history) > self._max_history:
            self.history = self.history[-self._max_history:]

        return result

    async def close(self) -> None:
        """Terminate the session and kill any active process."""
        if self._active_proc and self._active_proc.returncode is None:
            try:
                self._active_proc.terminate()
                await asyncio.wait_for(self._active_proc.wait(), timeout=5.0)
            except Exception:
                try:
                    self._active_proc.kill()
                except Exception:
                    pass
            self._active_proc = None


class TerminalManager:
    """Manages multiple terminal sessions."""

    def __init__(self, default_cwd: str) -> None:
        self.default_cwd = default_cwd
        self._sessions: dict[str, TerminalSession] = {}
        self._counter = 0

    def create_session(
        self,
        name: Optional[str] = None,
        cwd: Optional[str] = None,
    ) -> TerminalSession:
        """Create a new terminal session."""
        self._counter += 1
        session_id = name or f"term-{self._counter}"
        session = TerminalSession(
            session_id=session_id,
            cwd=cwd or self.default_cwd,
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[TerminalSession]:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def get_or_create_default(self) -> TerminalSession:
        """Get the default session, creating it if needed."""
        if "default" not in self._sessions:
            self.create_session(name="default")
        return self._sessions["default"]

    def list_sessions(self) -> list[str]:
        """List all session IDs."""
        return list(self._sessions.keys())

    async def close_session(self, session_id: str) -> bool:
        """Close and remove a session."""
        session = self._sessions.pop(session_id, None)
        if session:
            await session.close()
            return True
        return False

    async def close_all(self) -> None:
        """Close all sessions."""
        for session in self._sessions.values():
            await session.close()
        self._sessions.clear()
