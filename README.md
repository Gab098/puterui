# PuterUI

A lightweight terminal-based AI coding assistant powered by [Ollama](https://ollama.com). Think of it as a stripped-down, local-first alternative to tools like [OpenCode](https://github.com/anomalyco/opencode), [OpenClaw](https://github.com/openclaw/openclaw), and [OpenManus](https://github.com/FoundationAgents/OpenManus) -- no cloud API keys needed, just Ollama running on your machine.

## Features

- **Local-first**: Runs entirely on your machine via Ollama. No API keys, no cloud costs.
- **Tool-use agent loop**: The assistant can read/write/edit files, search code, fetch URLs, search the web, and run commands.
- **Persona / Soul system**: Give the assistant a configurable identity, personality, values, and rules (inspired by OpenClaw).
- **Skills system**: Load specialized instruction modules for code review, refactoring, git workflows, and more.
- **Terminal control**: Persistent shell sessions with working directory tracking -- like having a real terminal.
- **Browser control**: Navigate, click, type, screenshot, and run JS in your browser via Playwright or Selenium.
- **Lightweight**: Minimal dependencies (httpx, rich, prompt-toolkit, pydantic). No heavy frameworks.
- **Interactive REPL**: Rich terminal UI with markdown rendering and colored output.
- **One-shot mode**: Pass a prompt directly for scripting/CI use cases.
- **Safe by default**: Command allowlist for `run_command`, file access sandboxed to project directory.

## Requirements

- Python 3.9+
- [Ollama](https://ollama.com/download) installed and running

### Optional (for browser control)

- Playwright: `pip install puterui[browser-playwright] && playwright install chromium`
- Selenium: `pip install puterui[browser-selenium]`

## Installation

```bash
git clone https://github.com/Gab098/puterui.git
cd puterui
pip install -e ".[dev]"
```

## Quick Start

1. Make sure Ollama is running:
   ```bash
   ollama serve
   ```

2. Pull a model (if you haven't already):
   ```bash
   ollama pull qwen2.5-coder:7b
   ```

3. Start PuterUI:
   ```bash
   puterui
   ```

## Usage

### Interactive Mode

```
$ puterui
+------------------------------------------+
| PuterUI v0.1.0 - lightweight AI coding   |
| assistant                                 |
+------------------------------------------+
  Model: qwen2.5-coder:7b  |  Ollama: http://localhost:11434
  Persona: Puter (AI coding assistant)

you> Can you look at the project structure and explain what this does?
```

### One-shot Mode

```bash
puterui "List all Python files and summarize the project"
```

### CLI Options

```
puterui --help

options:
  --version, -v         Show version
  --model, -m MODEL     Ollama model to use
  --ollama-url, -u URL  Ollama API URL
  --project-dir, -p DIR Project directory
  --persona PATH        Path to a persona.toml file
  prompt                Optional one-shot prompt
```

## Persona / Soul System

The persona system gives the assistant a configurable identity. Create a `persona.toml` in your project or `~/.config/puterui/`:

```toml
name = "CodeWiz"
role = "senior backend engineer"

traits = [
    "opinionated about code quality",
    "prefers functional patterns",
    "dry humor",
]

communication_style = "casual-professional"

values = [
    "readability over cleverness",
    "test everything",
    "small focused functions",
]

quirks = [
    "uses cooking analogies for architecture decisions",
]

backstory = "A seasoned developer who has survived three rewrites and lived to tell the tale."

rules = [
    "Never commit directly to main",
    "Always run tests before suggesting a PR",
    "Explain trade-offs, not just solutions",
]
```

Use `/persona` in the REPL to see the current persona, or `/persona details` for the full prompt.

## Skills System

Skills are specialized instruction modules that enhance the assistant's capabilities for specific tasks.

### Built-in Skills

| Skill | Description |
|-------|-------------|
| Code Review | Systematic code review (bugs, security, performance, style) |
| Refactor | Safe incremental refactoring with behavior preservation |
| Git Workflow | Git best practices, conventional commits, branching |
| Adaptive Operator | Structured plan→execute→verify workflow for stronger results on small local models |
| Toolsmith | Build minimal new tools/skills when blocked and validate before use |

### Using Skills

```
you> /skill list
  Code Review [inactive] - Systematic code review...
  Refactor [inactive] - Safe incremental refactoring...
  Git Workflow [inactive] - Git operations and best practices...

you> /skill activate Code Review
  Skill 'Code Review' activated.

you> /skill deactivate Code Review
  Skill 'Code Review' deactivated.
```

### Custom Skills

Create `.puterui/skills/` in your project or `~/.config/puterui/skills/`:

**TOML format** (`my-skill.toml`):
```toml
name = "API Design"
description = "REST API design best practices"
tags = ["api", "rest"]
instructions = """
When designing APIs:
1. Use RESTful conventions
2. Version your endpoints
3. Return consistent error formats
"""
```

**Markdown format** (`my-skill.md`):
```markdown
# API Design
> REST API design best practices

When designing APIs:
1. Use RESTful conventions
2. Version your endpoints
3. Return consistent error formats
```

## Terminal Control

The assistant has full terminal access via persistent sessions that preserve state between commands:

```
you> Create a new Python virtualenv and install flask

  >> terminal_exec(command='python3 -m venv .venv')
  >> terminal_exec(command='source .venv/bin/activate && pip install flask')
```

Terminal sessions track:
- Working directory (persists across commands)
- Command history
- Exit codes

Manage sessions with `/terminal list` and `/terminal close <name>`.

## Browser Control

PuterUI can control a browser on your machine for web interaction:

```
you> /browser start

you> Go to github.com and search for "puterui"

  >> browser_navigate(url='https://github.com')
  >> browser_type(selector='input[name=q]', text='puterui')
  >> browser_click(selector='form button[type=submit]')
  >> browser_get_text()
```

### Browser Commands

| Command | Description |
|---------|-------------|
| `/browser start` | Start browser (auto-detects Playwright or Selenium) |
| `/browser start playwright` | Force Playwright backend |
| `/browser start selenium` | Force Selenium backend |
| `/browser stop` | Close the browser |
| `/browser status` | Check if browser is running |

### Browser Tools (used by the assistant)

| Tool | Description |
|------|-------------|
| `browser_navigate` | Open a URL |
| `browser_get_text` | Get visible text of current page |
| `browser_click` | Click an element by CSS selector |
| `browser_type` | Type text into an input |
| `browser_screenshot` | Take a screenshot |
| `browser_js` | Execute JavaScript |

## All Slash Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/quit` or `/exit` | Exit PuterUI |
| `/clear` | Clear conversation history |
| `/model <name>` | Switch to a different model |
| `/models` | List available Ollama models |
| `/config` | Show current configuration |
| `/compact` | Summarize conversation to save context |
| `/files` | List project files |
| `/persona` | Show current persona |
| `/persona details` | Full persona prompt |
| `/skill list` | List available skills |
| `/skill activate <name>` | Activate a skill |
| `/skill deactivate <name>` | Deactivate a skill |
| `/skill info <name>` | Show skill details |
| `/terminal list` | List terminal sessions |
| `/terminal close <name>` | Close a terminal session |
| `/browser start` | Start browser control |
| `/browser stop` | Stop browser |
| `/browser status` | Browser status |

## Configuration

Create `puterui.toml` in your project or `~/.config/puterui/`:

```toml
model = "qwen2.5-coder:7b"
ollama_url = "http://localhost:11434"
max_tokens = 4096
temperature = 0.1
max_iterations = 25

allowed_commands = [
    "ls", "cat", "head", "tail", "find", "grep", "wc",
    "git", "python", "pip", "npm", "node", "cargo", "go",
    "make", "echo", "pwd", "whoami", "date", "uname",
]
```

Environment variable overrides: `PUTERUI_OLLAMA_URL`, `PUTERUI_MODEL`

## All Tools

| Tool | Description |
|------|-------------|
| `read_file` | Read file contents with line numbers |
| `write_file` | Write/create files |
| `edit_file` | Replace exact strings in files |
| `list_files` | List directory contents |
| `search_files` | Regex search across files |
| `run_command` | Execute allowed shell commands (sandboxed) |
| `terminal_exec` | Execute in persistent terminal (full access) |
| `browser_navigate` | Open URL in browser |
| `browser_get_text` | Get page text |
| `browser_click` | Click element |
| `browser_type` | Type into input |
| `browser_screenshot` | Take screenshot |
| `browser_js` | Execute JavaScript |

## Recommended Models

| Model | Size | Notes |
|-------|------|-------|
| `qwen2.5-coder:7b` | ~4.7 GB | Default. Good balance of speed and quality |
| `qwen2.5-coder:1.5b` | ~1 GB | Fast, lighter on resources |
| `llama3.1:8b` | ~4.7 GB | Strong general-purpose model |
| `deepseek-coder-v2:16b` | ~8.9 GB | High quality code generation |
| `codellama:13b` | ~7.4 GB | Meta's code-focused model |

## Architecture

```
puterui/
  __init__.py          # Package metadata
  __main__.py          # python -m puterui entry point
  cli.py               # CLI argument parsing and REPL loop
  client.py            # Ollama API client (httpx-based)
  config.py            # Configuration management (TOML + env vars)
  agent.py             # Agent loop (LLM + tool orchestration)
  tools.py             # Tool definitions and implementations
  ui.py                # Terminal UI helpers (Rich-based)
  persona.py           # Persona / Soul identity system
  skills.py            # Skills registry and loader
  terminal.py          # Persistent terminal session manager
  browser.py           # Browser control (Playwright / Selenium)
  builtin_skills/      # Built-in skill definitions
    code-review.md
    refactor.md
    git-workflow.md
```

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check puterui/ tests/
ruff format puterui/ tests/
```

## License

MIT
