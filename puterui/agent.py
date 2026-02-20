"""Agent loop -- orchestrates the LLM and tool calls."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from puterui import ui
from puterui.client import OllamaClient, OllamaError
from puterui.config import Config
from puterui.tools import TOOL_DEFINITIONS, execute_tool

DEFAULT_SYSTEM_PROMPT = """\
You are PuterUI, a helpful AI coding assistant running in the user's terminal.
You have access to tools that let you read files, write files, edit files, \
list directories, search code, and run shell commands in the user's project.

Guidelines:
- Be concise and direct. Avoid unnecessary preamble.
- When the user asks you to make changes, use the available tools to do so.
- Always read relevant files before editing them.
- Explain what you're doing briefly before and after making changes.
- If a task is ambiguous, ask clarifying questions.
- For code changes, follow the project's existing style and conventions.
- When running commands, prefer safe read-only commands unless the user asks \
for modifications.
"""


class Agent:
    """Manages conversation state and the tool-use loop."""

    def __init__(self, config: Config, project_dir: Path) -> None:
        self.config = config
        self.project_dir = project_dir
        self.client = OllamaClient(config)
        self.messages: list[dict[str, Any]] = []

        system_prompt = config.system_prompt or DEFAULT_SYSTEM_PROMPT
        project_context = f"\nProject directory: {project_dir}\n"
        self.messages.append({
            "role": "system",
            "content": system_prompt + project_context,
        })

    async def close(self) -> None:
        await self.client.close()

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
            {"role": "system", "content": "Summarize the following conversation concisely."},
            {
                "role": "user",
                "content": "Summarize this conversation into key points and decisions:\n\n"
                + "\n".join(
                    f"[{m['role']}]: {m.get('content', '(tool call)')}"
                    for m in self.messages[1:]
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
                    {"role": "assistant", "content": f"[Conversation summary]: {summary}"},
                ]
                ui.print_success("Conversation compacted.")
            else:
                ui.print_warning("Could not generate summary.")
        except OllamaError as exc:
            ui.print_error(f"Failed to compact: {exc}")

    async def send(self, user_message: str) -> str:
        """Send a user message and run the agent loop. Returns the final text response."""
        self.messages.append({"role": "user", "content": user_message})

        for iteration in range(self.config.max_iterations):
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

                    # Execute
                    result = await execute_tool(
                        name=tool_name,
                        args=tool_args,
                        project_dir=self.project_dir,
                        allowed_commands=self.config.allowed_commands,
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
        summary = summary[:max_len - 3] + "..."
    return summary
