"""CLI entry point and interactive REPL for PuterUI."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from puterui import __version__, ui
from puterui.agent import Agent
from puterui.client import OllamaError
from puterui.config import Config
from puterui.persona import Persona
from puterui.skills import SkillRegistry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="puterui",
        description="PuterUI - lightweight AI coding assistant powered by Ollama",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"puterui {__version__}",
    )
    parser.add_argument(
        "--model",
        "-m",
        help="Ollama model to use (default: from config or qwen2.5-coder:7b)",
    )
    parser.add_argument(
        "--ollama-url",
        "-u",
        help="Ollama API URL (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--project-dir",
        "-p",
        help="Project directory to work in (default: current directory)",
    )
    parser.add_argument(
        "--persona",
        help="Path to a persona.toml file",
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Optional one-shot prompt (non-interactive mode)",
    )
    return parser.parse_args()


async def run_interactive(agent: Agent, config: Config) -> None:
    """Run the interactive REPL loop."""
    ui.print_banner()
    ui.print_model_info(config.model, config.ollama_url)

    # Show persona info
    ui.console.print(
        f"  Persona: [bold]{agent.persona.name}[/bold] "
        f"({agent.persona.role})",
        style="dim",
    )

    # Show active skills
    active = agent.skills.active
    if active:
        names = ", ".join(active.keys())
        ui.console.print(f"  Skills: [bold]{names}[/bold]", style="dim")

    available = agent.skills.available
    if available:
        ui.console.print(
            f"  Available skills: {', '.join(available.keys())} "
            "(use /skill activate <name>)",
            style="dim",
        )

    ui.console.print(
        "  Type [bold]/help[/bold] for commands, "
        "[bold]/quit[/bold] to exit.\n",
        style="dim",
    )

    # Check Ollama health
    healthy = await agent.client.check_health()
    if not healthy:
        ui.print_error(
            f"Cannot connect to Ollama at {config.ollama_url}\n"
            "  Make sure Ollama is running: ollama serve"
        )
        return

    input_buffer: list[str] = []

    while True:
        try:
            prompt_str = "... " if input_buffer else "you> "
            line = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input(prompt_str)
            )
        except (EOFError, KeyboardInterrupt):
            ui.console.print("\n[dim]Goodbye![/dim]")
            break

        # Handle multi-line input (line continuation with backslash)
        if line.endswith("\\"):
            input_buffer.append(line[:-1])
            continue

        if input_buffer:
            input_buffer.append(line)
            user_input = "\n".join(input_buffer)
            input_buffer.clear()
        else:
            user_input = line

        user_input = user_input.strip()
        if not user_input:
            continue

        # Handle slash commands
        if user_input.startswith("/"):
            handled = await _handle_command(user_input, agent, config)
            if handled == "quit":
                break
            continue

        # Send to agent
        await agent.send(user_input)


async def run_oneshot(agent: Agent, prompt: str) -> None:
    """Run a single prompt and exit."""
    healthy = await agent.client.check_health()
    if not healthy:
        ui.print_error(
            f"Cannot connect to Ollama at {agent.config.ollama_url}\n"
            "  Make sure Ollama is running: ollama serve"
        )
        return
    await agent.send(prompt)


async def _handle_command(
    cmd: str, agent: Agent, config: Config
) -> str | None:
    """Handle slash commands. Returns 'quit' to exit."""
    parts = cmd.split(maxsplit=1)
    command = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if command in ("/quit", "/exit", "/q"):
        ui.console.print("[dim]Goodbye![/dim]")
        return "quit"

    elif command == "/help":
        ui.print_help()

    elif command == "/clear":
        agent.clear_history()
        ui.print_success("Conversation history cleared.")

    elif command == "/compact":
        await agent.compact()

    elif command == "/model":
        if not arg:
            ui.print_info(f"Current model: {config.model}")
        else:
            config.model = arg.strip()
            agent.client.config.model = arg.strip()
            ui.print_success(f"Switched to model: {config.model}")

    elif command == "/models":
        try:
            models = await agent.client.list_models()
            if models:
                ui.print_info("Available models:")
                for m in models:
                    name = m.get("name", "unknown")
                    size = m.get("size", 0)
                    size_gb = size / (1024**3) if size else 0
                    ui.console.print(f"  - {name} ({size_gb:.1f} GB)")
            else:
                ui.print_warning(
                    "No models found. Pull one with: ollama pull <model>"
                )
        except OllamaError as exc:
            ui.print_error(str(exc))

    elif command == "/config":
        ui.print_info("Current configuration:")
        ui.console.print(f"  Model:          {config.model}")
        ui.console.print(f"  Ollama URL:     {config.ollama_url}")
        ui.console.print(f"  Max tokens:     {config.max_tokens}")
        ui.console.print(f"  Temperature:    {config.temperature}")
        ui.console.print(f"  Max iterations: {config.max_iterations}")
        ui.console.print(f"  Project dir:    {agent.project_dir}")

    elif command == "/files":
        from puterui.tools import tool_list_files

        result = await tool_list_files(
            {"path": ".", "recursive": False}, agent.project_dir
        )
        ui.console.print(result)

    elif command == "/persona":
        if not arg:
            ui.print_info(f"Current persona: {agent.persona.summary()}")
            if agent.persona.backstory:
                ui.console.print(f"  Backstory: {agent.persona.backstory}")
            if agent.persona.quirks:
                ui.console.print(
                    f"  Quirks: {', '.join(agent.persona.quirks)}"
                )
        else:
            ui.print_info("Persona details:")
            ui.console.print(agent.persona.to_system_prompt())

    elif command == "/skill":
        await _handle_skill_command(arg, agent)

    elif command == "/terminal":
        await _handle_terminal_command(arg, agent)

    elif command == "/browser":
        await _handle_browser_command(arg, agent)

    else:
        ui.print_warning(
            f"Unknown command: {command}. Type /help for available commands."
        )

    return None


async def _handle_skill_command(arg: str, agent: Agent) -> None:
    """Handle /skill subcommands."""
    parts = arg.split(maxsplit=1)
    subcmd = parts[0] if parts else ""
    skill_arg = parts[1].strip() if len(parts) > 1 else ""

    if subcmd == "list":
        available = agent.skills.available
        active = agent.skills.active
        if not available:
            ui.print_info("No skills available.")
            return
        ui.print_info("Skills:")
        for name, skill in available.items():
            status = "[green]active[/green]" if name in active else "inactive"
            desc = f" - {skill.description}" if skill.description else ""
            ui.console.print(f"  {name} [{status}]{desc}")

    elif subcmd == "activate" and skill_arg:
        if agent.skills.activate(skill_arg):
            agent.rebuild_system_prompt()
            ui.print_success(f"Skill '{skill_arg}' activated.")
        else:
            ui.print_error(f"Skill '{skill_arg}' not found.")

    elif subcmd == "deactivate" and skill_arg:
        if agent.skills.deactivate(skill_arg):
            agent.rebuild_system_prompt()
            ui.print_success(f"Skill '{skill_arg}' deactivated.")
        else:
            ui.print_error(f"Skill '{skill_arg}' not active.")

    elif subcmd == "info" and skill_arg:
        skill = agent.skills.available.get(skill_arg)
        if skill:
            ui.print_info(f"Skill: {skill.name}")
            if skill.description:
                ui.console.print(f"  Description: {skill.description}")
            if skill.tags:
                ui.console.print(f"  Tags: {', '.join(skill.tags)}")
            if skill.source_path:
                ui.console.print(f"  Source: {skill.source_path}")
        else:
            ui.print_error(f"Skill '{skill_arg}' not found.")

    else:
        ui.print_info(
            "Usage: /skill list | /skill activate <name> | "
            "/skill deactivate <name> | /skill info <name>"
        )


async def _handle_terminal_command(arg: str, agent: Agent) -> None:
    """Handle /terminal subcommands."""
    parts = arg.split(maxsplit=1)
    subcmd = parts[0] if parts else ""

    if subcmd == "list":
        sessions = agent.terminal.list_sessions()
        if sessions:
            ui.print_info("Terminal sessions:")
            for sid in sessions:
                session = agent.terminal.get_session(sid)
                if session:
                    ui.console.print(f"  {sid} (cwd: {session.cwd})")
        else:
            ui.print_info("No active terminal sessions.")

    elif subcmd == "close":
        name = parts[1].strip() if len(parts) > 1 else "default"
        closed = await agent.terminal.close_session(name)
        if closed:
            ui.print_success(f"Closed terminal session '{name}'.")
        else:
            ui.print_error(f"Session '{name}' not found.")

    else:
        ui.print_info(
            "Usage: /terminal list | /terminal close <name>\n"
            "  The assistant uses terminal_exec tool automatically."
        )


async def _handle_browser_command(arg: str, agent: Agent) -> None:
    """Handle /browser subcommands."""
    parts = arg.split(maxsplit=1)
    subcmd = parts[0] if parts else ""

    if subcmd == "start":
        backend = parts[1].strip() if len(parts) > 1 else None
        result = await agent.browser.start(backend)
        if result.success:
            ui.print_success(result.data)
        else:
            ui.print_error(result.error)

    elif subcmd == "stop":
        result = await agent.browser.close()
        if result.success:
            ui.print_success(result.data)
        else:
            ui.print_error(result.error)

    elif subcmd == "status":
        ui.print_info(f"Browser: {agent.browser.status()}")

    else:
        ui.print_info(
            "Usage: /browser start [playwright|selenium] | "
            "/browser stop | /browser status\n"
            "  The assistant uses browser tools automatically once started."
        )


async def async_main() -> None:
    args = parse_args()
    config = Config.load()

    # Apply CLI overrides
    if args.model:
        config.model = args.model
    if args.ollama_url:
        config.ollama_url = args.ollama_url

    project_dir = (
        Path(args.project_dir).resolve() if args.project_dir else Path.cwd()
    )

    # Load persona
    if args.persona:
        persona = Persona.load(Path(args.persona).parent)
    else:
        persona = Persona.load(project_dir)

    # Load skills
    skills = SkillRegistry()
    skills.load_builtin_skills()
    skills.load_user_skills()
    skills.load_project_skills(project_dir)

    agent = Agent(config, project_dir, persona=persona, skills=skills)

    try:
        if args.prompt:
            prompt = " ".join(args.prompt)
            await run_oneshot(agent, prompt)
        else:
            await run_interactive(agent, config)
    finally:
        await agent.close()


def main() -> None:
    """Synchronous entry point."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
