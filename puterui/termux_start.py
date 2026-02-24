"""Termux-friendly launcher for PuterUI (no root required)."""

from __future__ import annotations

import argparse
import hashlib
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


def _is_shared_storage_path(path: Path) -> bool:
    """Return True for Android shared-storage mounts (problematic for venv symlinks)."""
    resolved = path.resolve()
    as_posix = resolved.as_posix()
    return as_posix.startswith("/storage/") or as_posix.startswith("/sdcard/")


def choose_venv_dir(root: Path, env: dict[str, str] | None = None) -> Path:
    """Choose a Termux-safe venv directory.

    On shared storage, prefer an app-private/home path because creating venv
    symlinks (e.g. lib64 -> lib) often fails there.
    """
    env = env or os.environ

    if override := env.get("PUTERUI_TERMUX_VENV"):
        return Path(override).expanduser()

    in_termux = is_termux_environment(env)
    if in_termux and _is_shared_storage_path(root):
        root_hash = hashlib.sha1(str(root).encode("utf-8")).hexdigest()[:8]
        return Path.home() / ".local" / "share" / "puterui" / "venvs" / f"{root.name}-{root_hash}"

    return root / ".venv-termux"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    printable = " ".join(cmd)
    print(f"\n>> {printable}")
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def ensure_venv(root: Path, env: dict[str, str] | None = None) -> Path:
    """Create a local venv dedicated to Termux runs if it does not exist."""
    venv_dir = choose_venv_dir(root, env)
    py = _venv_python(venv_dir)
    if py.exists():
        return py

    print(f"Creating virtual environment ({venv_dir})...")
    venv_dir.parent.mkdir(parents=True, exist_ok=True)
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
    elif _is_shared_storage_path(root):
        print(
            "Detected shared storage checkout. Using a home-directory venv "
            "to avoid Termux permission/symlink issues."
        )

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
