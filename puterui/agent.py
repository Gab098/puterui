"""Agent loop -- orchestrates the LLM and tool calls."""

from __future__ import annotations

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
terminal session, and control a web browser on the user's machine.

Guidelines:
- Be concise and direct. Avoid unnecessary preamble.
- When the user asks you to make changes, use the available tools to do so.
- Always read relevant files before editing them.
- Explain what you are doing briefly before and after making changes.
- If a task is ambiguous, ask clarifying questions.
- For code changes, follow the project's existing style and conventions.
- Use terminal_exec for commands that need persistent state (cd, env vars).
- Use browser tools when asked to interact with web pages.
"""


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

        # Project context
        parts.append(f"\nProject directory: {self.project_dir}")

        self.messages = [
            {"role": "system", "content": "\n".join(parts)},
        ]

    def rebuild_system_prompt(self) -> None:
        """Rebuild system prompt (e.g. after activating a skill)."""
        old_messages = self.messages[1:] if len(self.messages) > 1 else []
        self._build_system_prompt()
        self.messages.extend(old_messages)

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

    async def _run_agent_loop(self) -> str:
        """Execute the agent loop (LLM call + tool execution cycle)."""

        for _iteration in range(self.config.max_iterations):
            try:
                response = await self.client.chat(
                    messages=self.messages,
                    tools=TOOL_DEFINITIONS,
                )
            except OllamaError as exc:
                error_msg = f"Ollama error: {exc}"
                ui.print_error(error_msg)
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

                    # Add tool result to messages
                    self.messages.append({
                        "role": "tool",
                        "content": result,
                    })

                # Continue the loop so the model can process tool results
                continue

            # No tool calls -- we have a final text response
            if content:
                ui.print_assistant(content)
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
