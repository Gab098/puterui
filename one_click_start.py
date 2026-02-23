#!/usr/bin/env python3
"""One-click cross-platform launcher for PuterUI.

What it does:
1) Ensures a local virtual environment exists (.venv)
2) Installs/updates project dependencies in editable mode
3) Starts PuterUI from that environment
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    printable = " ".join(cmd)
    print(f"\n>> {printable}")
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def ensure_venv() -> Path:
    py = _venv_python(VENV_DIR)
    if py.exists():
        return py

    print("Creating virtual environment (.venv)...")
    run([sys.executable, "-m", "venv", str(VENV_DIR)], cwd=ROOT)
    return py


def install_requirements(venv_python: Path) -> None:
    print("Installing PuterUI dependencies...")
    run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], cwd=ROOT)
    run([str(venv_python), "-m", "pip", "install", "-e", ".[dev]"], cwd=ROOT)


def start_puterui(venv_python: Path, args: list[str]) -> None:
    print("Starting PuterUI...")
    run([str(venv_python), "-m", "puterui", *args], cwd=ROOT)


def main() -> int:
    try:
        venv_python = ensure_venv()
        install_requirements(venv_python)
        start_puterui(venv_python, sys.argv[1:])
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"\nError: command failed with exit code {exc.returncode}")
        return exc.returncode or 1
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
