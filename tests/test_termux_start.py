from pathlib import Path

from puterui.termux_start import (
    _is_shared_storage_path,
    choose_venv_dir,
    is_termux_environment,
)


def test_is_termux_environment_true_with_prefix() -> None:
    assert is_termux_environment({"PREFIX": "/data/data/com.termux/files/usr"})


def test_is_termux_environment_true_with_termux_version() -> None:
    assert is_termux_environment({"TERMUX_VERSION": "0.118"})


def test_is_termux_environment_false() -> None:
    assert not is_termux_environment({"PREFIX": "/usr/local"})


def test_is_shared_storage_path_true() -> None:
    assert _is_shared_storage_path(Path("/storage/emulated/0/Download/puterui"))


def test_choose_venv_dir_uses_home_path_on_termux_shared_storage() -> None:
    root = Path("/storage/emulated/0/Download/puterui")
    env = {"PREFIX": "/data/data/com.termux/files/usr"}
    chosen = choose_venv_dir(root, env)
    assert "/.local/share/puterui/venvs/" in chosen.as_posix()


def test_choose_venv_dir_respects_override() -> None:
    root = Path("/storage/emulated/0/Download/puterui")
    env = {
        "PREFIX": "/data/data/com.termux/files/usr",
        "PUTERUI_TERMUX_VENV": "~/custom-venv",
    }
    chosen = choose_venv_dir(root, env)
    assert chosen.name == "custom-venv"
