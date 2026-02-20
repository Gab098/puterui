# PuterUI

A lightweight terminal-based AI coding assistant powered by [Ollama](https://ollama.com). Think of it as a stripped-down, local-first alternative to tools like [OpenCode](https://github.com/anomalyco/opencode) and [OpenClaw](https://github.com/openclaw/openclaw) -- no cloud API keys needed, just Ollama running on your machine.

## Features

- **Local-first**: Runs entirely on your machine via Ollama. No API keys, no cloud costs.
- **Tool-use agent loop**: The assistant can read, write, and edit files, search your codebase, and run shell commands.
- **Lightweight**: Minimal dependencies (httpx, rich, prompt-toolkit, pydantic). No heavy frameworks.
- **Interactive REPL**: Rich terminal UI with markdown rendering, syntax highlighting, and colored output.
- **One-shot mode**: Pass a prompt directly for scripting/CI use cases.
- **Configurable**: TOML config file, environment variables, and CLI flags.
- **Safe by default**: Command execution is restricted to an allowlist. File access is sandboxed to the project directory.

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com/download) installed and running

## Installation

```bash
# Clone the repo
git clone https://github.com/Gab098/puterui.git
cd puterui

# Install in development mode
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

   Or run it as a module:
   ```bash
   python -m puterui
   ```

## Usage

### Interactive Mode

Just run `puterui` in your project directory:

```
$ puterui
+------------------------------------------+
| PuterUI v0.1.0 - lightweight AI coding   |
| assistant                                 |
+------------------------------------------+
  Model: qwen2.5-coder:7b  |  Ollama: http://localhost:11434

you> Can you look at the project structure and explain what this codebase does?
```

### One-shot Mode

Pass a prompt directly for non-interactive use:

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
  prompt                Optional one-shot prompt
```

### Slash Commands

Inside the REPL:

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/quit` or `/exit` | Exit PuterUI |
| `/clear` | Clear conversation history |
| `/model <name>` | Switch to a different model |
| `/models` | List available Ollama models |
| `/config` | Show current configuration |
| `/compact` | Summarize conversation to save context |
| `/files` | List files in the project directory |

### Multi-line Input

End a line with `\` to continue on the next line:

```
you> Write a function that \
... takes a list and returns \
... the unique elements
```

## Configuration

Create a `puterui.toml` file in your project directory or `~/.config/puterui/puterui.toml`:

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

Environment variables override the config file:

- `PUTERUI_OLLAMA_URL` - Ollama API URL
- `PUTERUI_MODEL` - Model name

## Available Tools

The assistant has access to these tools:

| Tool | Description |
|------|-------------|
| `read_file` | Read file contents with line numbers |
| `write_file` | Write/create files |
| `edit_file` | Replace exact strings in files |
| `list_files` | List directory contents |
| `search_files` | Regex search across files |
| `run_command` | Execute allowed shell commands |

## Recommended Models

Any Ollama model with tool-calling support works. Some good options:

| Model | Size | Notes |
|-------|------|-------|
| `qwen2.5-coder:7b` | ~4.7 GB | Default. Good balance of speed and quality |
| `qwen2.5-coder:1.5b` | ~1 GB | Fast, lighter on resources |
| `llama3.1:8b` | ~4.7 GB | Strong general-purpose model |
| `deepseek-coder-v2:16b` | ~8.9 GB | High quality code generation |
| `codellama:13b` | ~7.4 GB | Meta's code-focused model |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check puterui/ tests/

# Format
ruff format puterui/ tests/
```

## Architecture

```
puterui/
  __init__.py    # Package metadata
  __main__.py    # python -m puterui entry point
  cli.py         # CLI argument parsing and REPL loop
  client.py      # Ollama API client (httpx-based)
  config.py      # Configuration management (TOML + env vars)
  agent.py       # Agent loop (LLM + tool orchestration)
  tools.py       # Tool definitions and implementations
  ui.py          # Terminal UI helpers (Rich-based)
```

## License

MIT
