"""Terminal UI helpers using Rich."""

from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme

THEME = Theme({
    "info": "cyan",
    "success": "green",
    "warning": "yellow",
    "error": "bold red",
    "tool": "magenta",
    "dim": "dim white",
})

console = Console(theme=THEME)


def print_banner() -> None:
    """Print the startup banner."""
    banner = Text()
    banner.append("PuterUI", style="bold cyan")
    banner.append(" v0.1.0", style="dim")
    banner.append(" - lightweight AI coding assistant", style="dim white")
    console.print(Panel(banner, border_style="cyan", padding=(0, 1)))


def print_model_info(model: str, url: str) -> None:
    """Print the active model and Ollama URL."""
    console.print(f"  Model: [bold]{model}[/bold]  |  Ollama: [dim]{url}[/dim]")
    console.print(
        "  Type [bold]/help[/bold] for commands, [bold]/quit[/bold] to exit.\n",
        style="dim",
    )


def print_assistant(text: str) -> None:
    """Render the assistant's response as Markdown."""
    md = Markdown(text)
    console.print(Panel(md, title="[bold cyan]assistant[/bold cyan]", border_style="cyan"))


def print_thinking(text: str) -> None:
    """Print a thinking/reasoning step."""
    console.print(f"  [dim italic]{text}[/dim italic]")


def print_tool_call(name: str, args_summary: str) -> None:
    """Print a tool call notification."""
    console.print(f"  [tool]>> {name}[/tool]({args_summary})")


def print_tool_result(result: str, truncate: int = 1500) -> None:
    """Print tool result output."""
    display = result if len(result) <= truncate else result[:truncate] + "\n... (truncated)"
    console.print(Panel(display, title="[dim]tool result[/dim]", border_style="dim"))


def print_error(msg: str) -> None:
    """Print an error message."""
    console.print(f"[error]Error:[/error] {msg}")


def print_info(msg: str) -> None:
    """Print an info message."""
    console.print(f"[info]{msg}[/info]")


def print_success(msg: str) -> None:
    """Print a success message."""
    console.print(f"[success]{msg}[/success]")


def print_warning(msg: str) -> None:
    """Print a warning message."""
    console.print(f"[warning]{msg}[/warning]")


def print_help() -> None:
    """Print available commands."""
    help_text = """
**Commands:**
- `/help` - Show this help message
- `/quit` or `/exit` - Exit PuterUI
- `/clear` - Clear conversation history
- `/model <name>` - Switch to a different model
- `/models` - List available models
- `/config` - Show current configuration
- `/compact` - Summarize conversation to save context
- `/files` - List files in the project directory

**Persona:**
- `/persona` - Show current persona identity
- `/persona details` - Show full persona prompt

**Skills:**
- `/skill list` - List available skills
- `/skill activate <name>` - Activate a skill
- `/skill deactivate <name>` - Deactivate a skill
- `/skill info <name>` - Show skill details

**Terminal:**
- `/terminal list` - List active terminal sessions
- `/terminal close <name>` - Close a terminal session

**Browser:**
- `/browser start [playwright|selenium]` - Start browser control
- `/browser stop` - Close the browser
- `/browser status` - Check browser status

**Tips:**
- Just type naturally to ask the assistant for help
- The assistant can read, write, edit files, and run commands
- It can control a persistent terminal (preserves cd, env vars)
- It can control your browser (navigate, click, type, screenshot)
- Multi-line input: end a line with `\\` to continue
"""
    console.print(Markdown(help_text))
