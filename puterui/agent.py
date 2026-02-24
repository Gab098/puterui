"""Agent loop -- orchestrates the LLM and tool calls."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from puterui import ui
from puterui.browser import BrowserController
from puterui.client import OllamaClient, OllamaError
from puterui.config import Config
from puterui.persona import Persona
from puterui.skills import SkillRegistry
from puterui.terminal import TerminalManager
from puterui.tools import TOOL_DEFINITIONS, execute_tool
from puterui.vision import build_image_message, extract_image_refs

BASE_SYSTEM_PROMPT = """\
You are a coding assistant running in the user's terminal.
You have access to tools that let you read files, write files, edit files, \
list directories, search code, run shell commands, control a persistent \
terminal session, fetch web URLs for recon/API inspection, and control \
a web browser on the user's machine.

Guidelines:
- Be concise and direct. Avoid unnecessary preamble.
- When the user asks you to make changes, use the available tools to do so.
- Always read relevant files before editing them.
- Explain what you are doing briefly before and after making changes.
- If a task is ambiguous, ask clarifying questions.
- For code changes, follow the project's existing style and conventions.
- Use terminal_exec for commands that need persistent state (cd, env vars).
- Use browser tools when asked to interact with web pages.
- For smaller models, use a strict loop: PLAN (short bullets) -> EXECUTE \
  (tools/commands) -> VERIFY (tests/checks) -> REPORT (result + next steps).
- Prefer deterministic actions over guesswork: inspect files, run checks, cite evidence.
- For security and bug bounty workflows: stay in authorized scope, avoid destructive actions,
  and produce reproducible findings with impact + remediation.
- Think outside the box: when blocked, pivot strategies and compare alternatives
  using search_web/fetch_url.
- If a missing capability blocks progress, propose and implement a minimal new tool or skill,
  then validate it with tests before using it.
- When the task has multiple independent workstreams, propose mini-agents (sub-agents),
  each with a focused goal, and keep their progress explicit.
"""


@dataclass
class MiniAgent:
    """Lightweight sub-agent tracker for multitask workflows."""

    name: str
    goal: str
    status: str = "planned"


class Agent:
    """Manages conversation state and the tool-use loop."""

    def __init__(
        self,
        config: Config,
        project_dir: Path,
        persona: Optional[Persona] = None,
        skills: Optional[SkillRegistry] = None,
    ) -> None:
        self.config = config
        self.project_dir = project_dir
        self.client = OllamaClient(config)
        self.persona = persona or Persona()
        self.skills = skills or SkillRegistry()
        self.terminal = TerminalManager(str(project_dir))
        self.browser = BrowserController()
        self.messages: list[dict[str, Any]] = []
        self.mini_agents: dict[str, MiniAgent] = {}
        self._tools_supported = True
        self._task_log_path = self.project_dir / ".puterui" / "tasks.log"

        self._build_system_prompt()

    def _build_system_prompt(self) -> None:
        """Construct the system prompt from persona, skills, and config."""
        parts = []

        # Persona identity
        parts.append(self.persona.to_system_prompt())
        parts.append("")

        # Base capabilities
        if self.config.system_prompt:
            parts.append(self.config.system_prompt)
        else:
            parts.append(BASE_SYSTEM_PROMPT)

        # Active skills
        skills_prompt = self.skills.get_active_prompt()
        if skills_prompt:
            parts.append(skills_prompt)

        # Mini-agents context
        mini_prompt = self.get_mini_agents_prompt()
        if mini_prompt:
            parts.append(mini_prompt)

        # Project context
        parts.append(f"\nProject directory: {self.project_dir}")

        self.messages = [
            {"role": "system", "content": "\n".join(parts)},
        ]

    def create_mini_agent(self, name: str, goal: str) -> str:
        key = name.strip()
        if not key:
            return "Error: mini-agent name cannot be empty."
        if not goal.strip():
            return "Error: mini-agent goal cannot be empty."
        self.mini_agents[key] = MiniAgent(name=key, goal=goal.strip())
        self.rebuild_system_prompt()
        return f"Mini-agent '{key}' created."

    def update_mini_agent_status(self, name: str, status: str) -> str:
        agent = self.mini_agents.get(name)
        if agent is None:
            return f"Error: mini-agent '{name}' not found."
        allowed = {"planned", "running", "blocked", "done"}
        norm = status.strip().lower()
        if norm not in allowed:
            return f"Error: invalid status '{status}'. Allowed: {', '.join(sorted(allowed))}"
        agent.status = norm
        self.rebuild_system_prompt()
        return f"Mini-agent '{name}' set to {norm}."

    def remove_mini_agent(self, name: str) -> str:
        if name not in self.mini_agents:
            return f"Error: mini-agent '{name}' not found."
        del self.mini_agents[name]
        self.rebuild_system_prompt()
        return f"Mini-agent '{name}' removed."

    def list_mini_agents(self) -> list[MiniAgent]:
        return list(self.mini_agents.values())

    def get_mini_agents_prompt(self) -> str:
        if not self.mini_agents:
            return ""
        lines = ["\n# Active Mini-Agents"]
        for ma in self.mini_agents.values():
            lines.append(f"- {ma.name} [{ma.status}]: {ma.goal}")
        return "\n".join(lines)

    def rebuild_system_prompt(self) -> None:
        """Rebuild system prompt (e.g. after activating a skill)."""
        old_messages = self.messages[1:] if len(self.messages) > 1 else []
        self._build_system_prompt()
        self.messages.extend(old_messages)

    def _append_task_log(self, event: str, payload: dict[str, Any]) -> None:
        """Append structured task events to .puterui/tasks.log."""
        try:
            self._task_log_path.parent.mkdir(parents=True, exist_ok=True)
            record = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "event": event,
                "payload": payload,
            }
            with self._task_log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            # Logging must never break agent flow.
            return

    async def _chat_with_streaming(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
    ) -> tuple[dict[str, Any], bool]:
        """Call Ollama with streaming; return assembled response and whether text was streamed."""
        content_parts: list[str] = []
        last_message: dict[str, Any] = {}
        streamed_text = False

        if not hasattr(self.client, "chat_stream"):
            response = await self.client.chat(messages=messages, tools=tools)
            return response, False

        async for chunk in self.client.chat_stream(messages=messages, tools=tools):
            message = chunk.get("message", {})
            if message:
                last_message = {**last_message, **message}
            piece = message.get("content", "")
            if piece:
                if not streamed_text:
                    ui.print_stream_start()
                    streamed_text = True
                ui.print_stream_chunk(piece)
                content_parts.append(piece)

        if streamed_text:
            ui.print_stream_end()
            last_message["content"] = "".join(content_parts)

        return {"message": last_message}, streamed_text

    def on_model_switch(self) -> None:
        """Reset per-model runtime capability flags after switching model."""
        self._tools_supported = True

    async def close(self) -> None:
        await self.client.close()
        await self.terminal.close_all()
        await self.browser.close()

    def clear_history(self) -> None:
        """Clear conversation history, keeping the system prompt."""
        system = self.messages[0] if self.messages else None
        self.messages.clear()
        if system:
            self.messages.append(system)

    async def compact(self) -> None:
        """Summarize the conversation to reduce context size."""
        if len(self.messages) <= 2:
            ui.print_info("Nothing to compact.")
            return

        summary_request = [
            {
                "role": "system",
                "content": "Summarize the following conversation concisely.",
            },
            {
                "role": "user",
                "content": (
                    "Summarize this conversation into key points "
                    "and decisions:\n\n"
                    + "\n".join(
                        f"[{m['role']}]: {m.get('content', '(tool call)')}"
                        for m in self.messages[1:]
                    )
                ),
            },
        ]

        try:
            resp = await self.client.chat(summary_request)
            summary = resp.get("message", {}).get("content", "")
            if summary:
                system = self.messages[0]
                self.messages = [
                    system,
                    {
                        "role": "assistant",
                        "content": f"[Conversation summary]: {summary}",
                    },
                ]
                ui.print_success("Conversation compacted.")
            else:
                ui.print_warning("Could not generate summary.")
        except OllamaError as exc:
            ui.print_error(f"Failed to compact: {exc}")

    async def send(self, user_message: str) -> str:
        """Send a user message and run the agent loop.

        Automatically detects image references in the message
        (e.g. [image: path.png] or bare paths like ./screenshot.png)
        and sends them as multimodal messages for vision-capable models.

        Returns the final text response.
        """
        cleaned, image_paths = extract_image_refs(user_message)
        if image_paths:
            return await self.send_with_images(cleaned, image_paths)

        self.messages.append({"role": "user", "content": user_message})
        self._append_task_log("user_prompt", {"text": user_message})
        return await self._run_agent_loop()

    async def send_with_images(
        self, text: str, image_paths: list[str]
    ) -> str:
        """Send a message with attached images for vision models.

        Images are base64-encoded and sent in the Ollama `images` field.
        """
        message = build_image_message(text, image_paths, self.project_dir)
        n_images = len(message.get("images", []))
        if n_images > 0:
            ui.print_info(f"Attached {n_images} image(s) to message.")
        else:
            ui.print_warning(
                "No valid images found at the given paths. "
                "Sending as text-only."
            )
        self.messages.append(message)
        return await self._run_agent_loop()

    def _is_tools_unsupported_error(self, exc: OllamaError) -> bool:
        """Detect provider errors indicating the selected model cannot use tools."""
        msg = str(exc).lower()
        return "does not support tools" in msg or "unsupported tools" in msg

    async def _run_agent_loop(self) -> str:
        """Execute the agent loop (LLM call + tool execution cycle)."""

        for _iteration in range(self.config.max_iterations):
            tools_payload = TOOL_DEFINITIONS if self._tools_supported else None
            streamed_text = False
            try:
                response, streamed_text = await self._chat_with_streaming(
                    messages=self.messages,
                    tools=tools_payload,
                )
                if not response.get("message"):
                    response = await self.client.chat(
                        messages=self.messages,
                        tools=tools_payload,
                    )
            except OllamaError as exc:
                if self._tools_supported and self._is_tools_unsupported_error(exc):
                    self._tools_supported = False
                    ui.print_warning(
                        "Current model does not support tool-calls. "
                        "Retrying in text-only mode."
                    )
                    try:
                        response = await self.client.chat(
                            messages=self.messages,
                            tools=None,
                        )
                        streamed_text = False
                    except OllamaError as inner_exc:
                        error_msg = f"Ollama error: {inner_exc}"
                        ui.print_error(error_msg)
                        self._append_task_log("error", {"message": error_msg})
                        return error_msg
                else:
                    error_msg = f"Ollama error: {exc}"
                    if "connection error" in str(exc).lower():
                        ui.print_warning(
                            "Model request failed with a connection error. "
                            "Ollama may be up, but the selected model/backend may be unavailable."
                        )
                    ui.print_error(error_msg)
                    self._append_task_log("error", {"message": error_msg})
                    return error_msg

            message = response.get("message", {})
            content = message.get("content", "")
            tool_calls = message.get("tool_calls", [])

            # Add the assistant message to history
            self.messages.append(message)

            # If there are tool calls, execute them
            if tool_calls:
                for tc in tool_calls:
                    func = tc.get("function", {})
                    tool_name = func.get("name", "unknown")
                    tool_args = func.get("arguments", {})

                    # Show the tool call in the UI
                    args_summary = _summarize_args(tool_args)
                    ui.print_tool_call(tool_name, args_summary)
                    self._append_task_log("tool_call", {"name": tool_name, "args": tool_args})

                    # Execute with all contexts
                    result = await execute_tool(
                        name=tool_name,
                        args=tool_args,
                        project_dir=self.project_dir,
                        allowed_commands=self.config.allowed_commands,
                        terminal_manager=self.terminal,
                        browser=self.browser,
                    )

                    ui.print_tool_result(result)
                    self._append_task_log(
                        "tool_result",
                        {"name": tool_name, "result": result[:800]},
                    )

                    # Add tool result to messages
                    self.messages.append({
                        "role": "tool",
                        "content": result,
                    })

                # Continue the loop so the model can process tool results
                continue

            # No tool calls -- we have a final text response
            if content and not streamed_text:
                ui.print_assistant(content)
            if content:
                self._append_task_log("assistant_response", {"text": content[:1500]})
            return content

        # Exhausted iterations
        exhaust_msg = (
            "Reached maximum tool-call iterations. "
            "Please try again with a simpler request."
        )
        ui.print_warning(exhaust_msg)
        return exhaust_msg


def _summarize_args(args: dict[str, Any], max_len: int = 80) -> str:
    """Create a short summary of tool arguments for display."""
    parts = []
    for k, v in args.items():
        val_str = str(v)
        if len(val_str) > 40:
            val_str = val_str[:37] + "..."
        parts.append(f"{k}={val_str!r}")
    summary = ", ".join(parts)
    if len(summary) > max_len:
        summary = summary[: max_len - 3] + "..."
    return summary
