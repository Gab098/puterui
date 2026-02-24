"""Termux-friendly launcher for PuterUI (no root required)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def is_termux_environment(env: dict[str, str] | None = None) -> bool:
    """Best-effort check for Termux runtime."""
    env = env or os.environ
    prefix = env.get("PREFIX", "")
    return (
        "com.termux" in prefix
        or "TERMUX_VERSION" in env
        or Path("/data/data/com.termux").exists()
    )


def _venv_python(venv_dir: Path) -> Path:
    return venv_dir / "bin" / "python"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    printable = " ".join(cmd)
    print(f"\n>> {printable}")
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def ensure_venv(root: Path, venv_name: str = ".venv-termux") -> Path:
    """Create a local venv dedicated to Termux runs if it does not exist."""
    venv_dir = root / venv_name
    py = _venv_python(venv_dir)
    if py.exists():
        return py

    print(f"Creating virtual environment ({venv_name})...")
    run([sys.executable, "-m", "venv", str(venv_dir)], cwd=root)
    return py


def install_requirements(venv_python: Path, root: Path, include_dev: bool = False) -> None:
    """Install PuterUI in editable mode inside the local venv."""
    print("Installing PuterUI dependencies (no root)...")
    run(
        [
            str(venv_python),
            "-m",
            "pip",
            "install",
            "--upgrade",
            "pip",
            "setuptools",
            "wheel",
        ],
        cwd=root,
    )
    extras = ".[dev]" if include_dev else "."
    run([str(venv_python), "-m", "pip", "install", "-e", extras], cwd=root)


def start_puterui(venv_python: Path, args: list[str], root: Path) -> None:
    """Launch PuterUI with the requested CLI args."""
    print("Starting PuterUI...")
    run([str(venv_python), "-m", "puterui", *args], cwd=root)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Termux launcher for PuterUI (no root required)."
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Install with dev dependencies (.[dev]).",
    )
    parser.add_argument(
        "puterui_args",
        nargs=argparse.REMAINDER,
        help="Arguments passed through to puterui.",
    )
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parent.parent

    if not is_termux_environment():
        print("Warning: Termux environment not detected; continuing anyway.")

    passthrough = args.puterui_args
    if passthrough and passthrough[0] == "--":
        passthrough = passthrough[1:]

    try:
        venv_python = ensure_venv(root)
        install_requirements(venv_python, root, include_dev=args.dev)
        start_puterui(venv_python, passthrough, root)
        return 0
    except subprocess.CalledProcessError as exc:
        print(f"\nError: command failed with exit code {exc.returncode}")
        return exc.returncode or 1
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
